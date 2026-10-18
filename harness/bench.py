"""In-container benchmark entry point (runs as root inside the Modal GPU container).

Sequence: hash harness + candidate, check GPU, launch candidate/serve.sh as an
unprivileged user, scan for foreign weights while it boots, wait for ready,
run the seeded workload, kill the server, sign the record.
"""

from __future__ import annotations

import json
import os
import secrets
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

from harness import config
from harness.client import run_benchmark, wait_ready
from harness.integrity import harness_hash, scan_foreign_weights, sign, tree_hash

CANDIDATE_DIR = Path("/candidate")
HMAC_ENV = "SPEEDRUN_HMAC_KEY"


class HFTokenizer:
    def __init__(self, path: str):
        from tokenizers import Tokenizer

        self._tok = Tokenizer.from_file(path)

    def encode(self, text: str) -> list[int]:
        return self._tok.encode(text, add_special_tokens=False).ids

    def decode(self, ids: list[int]) -> str:
        return self._tok.decode(ids, skip_special_tokens=False)


def log(msg: str) -> None:
    print(f"[bench {time.strftime('%H:%M:%S')}] {msg}", file=sys.stderr, flush=True)


def gpu_info() -> str:
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"],
        capture_output=True, text=True, check=False,
    )
    return out.stdout.strip() or out.stderr.strip()


def server_env() -> dict:
    env = {k: v for k, v in os.environ.items() if k != HMAC_ENV and not k.startswith("MODAL_")}
    # Modal's runtime dir (/pkg) is root-only; drop it so the server's python doesn't try to import from it.
    env["PYTHONPATH"] = ":".join(p for p in env.get("PYTHONPATH", "").split(":") if p and not p.startswith("/pkg"))
    env.update(
        HOME="/cache/home",  # JIT/autotune caches land under $HOME/.cache; persist them across runs
        MODEL_DIR=config.MODEL_DIR,
        MODELS_ROOT="/models",
        CACHE_DIR="/cache",
        PORT=str(config.SERVER_PORT),
        XDG_CACHE_HOME="/cache/xdg",
        TRITON_CACHE_DIR="/cache/triton",
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
    )
    return env


def launch_server(log_path: Path) -> subprocess.Popen:
    for d in ("/cache/home", "/cache/xdg", "/cache/triton"):
        os.makedirs(d, exist_ok=True)
    os.chmod("/cache", 0o777)
    subprocess.run(["chmod", "-R", "a+rwX", "/cache"], check=False)
    logf = open(log_path, "w")
    return subprocess.Popen(
        ["bash", str(CANDIDATE_DIR / "serve.sh")],
        cwd="/cache/home",
        env=server_env(),
        stdout=logf,
        stderr=subprocess.STDOUT,
        user=config.SERVER_UID,
        group=config.SERVER_UID,
        extra_groups=[],
        process_group=0,
    )


def stop_server(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    for sig, wait in ((signal.SIGTERM, 15), (signal.SIGKILL, 5)):
        try:
            os.killpg(proc.pid, sig)
            proc.wait(timeout=wait)
            return
        except (ProcessLookupError, subprocess.TimeoutExpired):
            continue


def head_tail(path: Path, head: int = 120, tail: int = 40) -> str:
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return ""
    if len(lines) <= head + tail:
        return "\n".join(lines)
    return "\n".join(lines[:head] + [f"... {len(lines) - head - tail} lines omitted ..."] + lines[-tail:])


def main(out_path: str) -> None:
    t0 = time.monotonic()
    key = os.environ.pop(HMAC_ENV, "").encode()
    record: dict = {
        "schema": 1,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "harness_hash": harness_hash(),
        "candidate_hash": tree_hash(CANDIDATE_DIR),
        "model_repo": config.MODEL_REPO,
        "model_revision": config.MODEL_REVISION,
        "gpu": gpu_info(),
        "violations": [],
    }
    log(f"harness={record['harness_hash'][:12]} candidate={record['candidate_hash'][:12]} gpu={record['gpu']}")
    if not key:
        record["violations"].append("no signing key in environment")
    if config.GPU_NAME_MUST_CONTAIN not in record["gpu"]:
        record["violations"].append(f"wrong GPU: {record['gpu']!r}")

    log_path = Path("/tmp/server.log")
    proc = launch_server(log_path)
    foreign: list[str] = []
    scanner = threading.Thread(target=lambda: foreign.extend(scan_foreign_weights(["/"], ["/models"])))
    scanner.start()
    try:
        wait_ready("127.0.0.1", config.SERVER_PORT, config.SERVER_READY_TIMEOUT_S, lambda: proc.poll() is None)
        record["startup_s"] = round(time.monotonic() - t0, 2)
        log(f"server ready after {record['startup_s']}s")
        scanner.join()
        if foreign:
            record["violations"].append(f"foreign weight files outside /models: {foreign[:5]}")
        seed = secrets.randbits(63)
        record["seed"] = seed
        tok = HFTokenizer(f"{config.MODEL_DIR}/tokenizer.json")
        t_bench = time.monotonic()
        result = run_benchmark("127.0.0.1", config.SERVER_PORT, tok, seed, log=log)
        record["bench_s"] = round(time.monotonic() - t_bench, 2)
        record["violations"] += result.pop("violations")
        record.update(result)
    except Exception as e:  # noqa: BLE001 - any failure is an invalid run, not a crash
        record["violations"].append(f"{type(e).__name__}: {e}")
    finally:
        stop_server(proc)
        scanner.join()

    if harness_hash() != record["harness_hash"]:
        record["violations"].append("harness files changed during the run")
    record["container_s"] = round(time.monotonic() - t0, 2)
    record["server_log"] = head_tail(log_path)
    out = {"record": record, "signature": sign(record, key) if key else ""}
    Path(out_path).write_text(json.dumps(out))
    log(f"done in {record['container_s']}s, violations={len(record['violations'])}")


if __name__ == "__main__":
    main(sys.argv[1])
