"""Modal app: weight download, the benchmark run, and signature verification."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

import modal

from candidate.image import build_image
from harness import config

ROOT = Path(__file__).resolve().parent.parent

app = modal.App("glm-flash-speedrun")
models_vol = modal.Volume.from_name(config.VOLUME_MODELS, create_if_missing=True)
cache_vol = modal.Volume.from_name(config.VOLUME_CACHE, create_if_missing=True)
hmac_secret = modal.Secret.from_name(config.HMAC_SECRET)

# Candidate layers first, frozen layers last: the bench deps, harness and an
# unprivileged server user are added on top of whatever the candidate built.
bench_image = (
    build_image()
    .run_commands(
        f"id -u {config.SERVER_UID} >/dev/null 2>&1 || useradd -m -u {config.SERVER_UID} speedrun-server",
        "python3 -m pip install --no-cache-dir --target /opt/bench/site tokenizers==0.23.3",
    )
    .add_local_dir(ROOT / "harness", "/opt/bench/src/harness", copy=True, ignore=["**/__pycache__", "**/.DS_Store"])
    .add_local_dir(ROOT / "candidate", "/candidate", copy=True, ignore=["**/__pycache__", "**/.DS_Store"])
    .run_commands("chmod -R a-w /opt/bench /candidate")
    .add_local_python_source("candidate")
)

# Every container re-imports this module, so every image needs the candidate package.
download_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("huggingface_hub[hf_xet]==2.2.0")
    .add_local_python_source("candidate")
)
util_image = modal.Image.debian_slim(python_version="3.12").add_local_python_source("candidate")
convert_image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("torch==2.14.1", index_url="https://download.pytorch.org/whl/cpu")
    .pip_install("safetensors==0.8.0", "numpy==2.5.4")
    .add_local_python_source("candidate")
)


def extra_models() -> list[tuple[str, str]]:
    """candidate/extra_models.txt: `repo@revision` per line (e.g. speculative draft heads)."""
    path = ROOT / "candidate" / "extra_models.txt"
    pairs = []
    for line in path.read_text().splitlines() if path.exists() else []:
        line = line.split("#")[0].strip()
        if line:
            repo, rev = line.split("@")
            pairs.append((repo.strip(), rev.strip()))
    return pairs


@app.function(image=download_image, volumes={"/models": models_vol}, cpu=8, memory=16384, timeout=4 * 3600)
def download(repos: list[tuple[str, str]]) -> list[str]:
    from huggingface_hub import snapshot_download

    done = []
    for repo, rev in repos:
        target = f"/models/{repo}/{rev}"
        if Path(target, ".complete").exists():
            done.append(f"{repo}@{rev} (cached)")
            continue
        snapshot_download(repo, revision=rev, local_dir=target, max_workers=32)
        Path(target, ".complete").write_text(rev)
        models_vol.commit()
        done.append(f"{repo}@{rev}")
    return done


@app.function(image=convert_image, volumes={"/models": models_vol}, cpu=16, memory=131072, timeout=4 * 3600)
def convert(script: str) -> str:
    """Run candidate/convert.py on the pinned checkpoint; output is keyed by the script's hash.

    Derived weights can only come from the pinned weights through a public script, and the
    benchmark still mounts the volume read-only and quality-gates the result.
    """
    import hashlib

    sha = hashlib.sha256(script.encode()).hexdigest()[:16]
    out = Path(config.DERIVED_ROOT) / sha
    if (out / ".complete").exists():
        return f"derived/{sha} (cached)"
    # Write in place (renaming a directory on a Modal volume leaves its files unopenable
    # from other containers); `.complete`, written last, is what marks the output usable.
    subprocess.run(["rm", "-rf", str(out)], check=True)
    out.mkdir(parents=True)
    script_path = Path("/tmp/convert.py")
    script_path.write_text(script)
    subprocess.run(["python", str(script_path), config.MODEL_DIR, str(out)], check=True)
    models_vol.commit()
    (out / ".complete").write_text(sha)
    models_vol.commit()
    return f"derived/{sha}"


@app.function(
    image=bench_image,
    gpu=config.GPU,
    cpu=config.CPU_CORES,
    memory=config.MEMORY_MIB,
    volumes={"/models": models_vol.read_only(), "/cache": cache_vol},
    secrets=[hmac_secret],
    block_network=True,
    timeout=config.RUN_TIMEOUT_S,
    single_use_containers=True,
)
def bench(_i: int = 0) -> dict:
    out_dir = tempfile.mkdtemp()  # mode 0700, root-only: the server user cannot forge it
    out_path = os.path.join(out_dir, "result.json")
    subprocess.run(["python3", "-E", "-s", "/opt/bench/src/harness/_entry.py", out_path], check=False)
    if not os.path.exists(out_path):
        return {"record": {"violations": ["bench produced no result"]}, "signature": ""}
    cache_vol.commit()
    return json.loads(Path(out_path).read_text())


@app.function(image=util_image, secrets=[hmac_secret], cpu=1, memory=1024, timeout=300)
def verify(items: list[dict]) -> list[bool]:
    from harness.integrity import verify as verify_sig

    key = os.environ["SPEEDRUN_HMAC_KEY"].encode()
    return [bool(it.get("signature")) and verify_sig(it["record"], it["signature"], key) for it in items]
