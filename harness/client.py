"""Streaming benchmark client. All timing and token counting happens here, never on the server."""

from __future__ import annotations

import http.client
import json
import statistics
import time
import zlib
from dataclasses import dataclass, field
from typing import Callable

from harness import config
from harness.workload import Request, Tokenizer, build_schedule, grade


@dataclass
class StreamResult:
    status: int
    text: str = ""
    chunk_times: list[float] = field(default_factory=list)  # seconds after send, non-empty chunks only
    chunk_texts: list[str] = field(default_factory=list)
    finish_reason: str | None = None
    error: str | None = None


def get_model_id(host: str, port: int, timeout: float = 5.0) -> str:
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        conn.request("GET", "/v1/models")
        resp = conn.getresponse()
        if resp.status != 200:
            raise RuntimeError(f"/v1/models returned {resp.status}")
        return json.loads(resp.read())["data"][0]["id"]
    finally:
        conn.close()


def wait_ready(host: str, port: int, timeout_s: float, alive: Callable[[], bool]) -> str:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if not alive():
            raise RuntimeError("server process exited before becoming ready")
        try:
            return get_model_id(host, port)
        except (OSError, RuntimeError, ValueError, KeyError, IndexError):
            time.sleep(0.5)
    raise TimeoutError(f"server not ready after {timeout_s}s")


def stream_completion(host: str, port: int, model: str, req: Request) -> StreamResult:
    body = json.dumps(
        {
            "model": model,
            "prompt": req.prompt,
            "max_tokens": req.max_tokens,
            "temperature": 0.0,
            "stream": True,
            "ignore_eos": req.ignore_eos,
            "skip_special_tokens": True,
        }
    ).encode()
    conn = http.client.HTTPConnection(host, port, timeout=config.REQUEST_TIMEOUT_S)
    try:
        conn.connect()
        t0 = time.perf_counter()
        conn.request("POST", "/v1/completions", body, {"Content-Type": "application/json"})
        resp = conn.getresponse()
        res = StreamResult(status=resp.status)
        if resp.status != 200:
            res.error = resp.read()[:500].decode(errors="replace")
            return res
        while True:
            line = resp.readline()
            if not line:
                break
            if not line.startswith(b"data:"):
                continue
            payload = line[5:].strip()
            if payload == b"[DONE]":
                break
            now = time.perf_counter() - t0
            choice = json.loads(payload)["choices"][0]
            text = choice.get("text") or ""
            if text:
                res.chunk_times.append(now)
                res.chunk_texts.append(text)
            res.finish_reason = choice.get("finish_reason") or res.finish_reason
        res.text = "".join(res.chunk_texts)
        return res
    except (OSError, ValueError, KeyError, IndexError) as e:
        return StreamResult(status=-1, error=repr(e))
    finally:
        conn.close()


def compress_ratio(text: str) -> float:
    raw = text.encode()
    return len(zlib.compress(raw, 9)) / max(len(raw), 1)


def measure_timed(res: StreamResult, tok: Tokenizer) -> dict:
    """TTFT and decode tok/s for one streamed timed request, plus integrity violations."""
    violations = []
    if res.status != 200 or res.error:
        return {"violations": [f"http status={res.status} error={res.error}"]}
    if len(res.chunk_times) < 2:
        return {"violations": ["fewer than 2 streamed chunks"]}
    if res.finish_reason != "length":
        violations.append(f"finish_reason={res.finish_reason!r}, expected 'length' (ignore_eos)")

    counted = len(tok.encode(res.text))
    if abs(counted - config.OUTPUT_TOKENS) > config.OUTPUT_TOKENS * config.OUTPUT_TOKENS_TOLERANCE:
        violations.append(f"output re-tokenizes to {counted} tokens, expected {config.OUTPUT_TOKENS}")
    tokens = min(counted, config.OUTPUT_TOKENS)  # inflating text can never help

    times = res.chunk_times
    gap = statistics.median(b - a for a, b in zip(times, times[1:]))
    # A token streamed before prefill finished would make later chunks arrive
    # "late" relative to a steady decode cadence; charge that lateness to TTFT.
    lookback = min(config.TTFT_LOOKBACK_CHUNKS, len(times))
    ttft = max(times[i] - i * gap for i in range(lookback))
    first_tokens = len(tok.encode(res.chunk_texts[0]))
    decode_s = times[-1] - times[0]
    tps = (tokens - first_tokens) / decode_s if decode_s > 0 else float("inf")
    return {
        "ttft_ms": ttft * 1000,
        "ttft_raw_ms": times[0] * 1000,
        "tps": tps,
        "tokens": counted,
        "chunks": len(times),
        "compress_ratio": compress_ratio(res.text),
        "violations": violations,
    }


def run_benchmark(host: str, port: int, tok: Tokenizer, seed: int, log: Callable[[str], None] = print) -> dict:
    model = get_model_id(host, port)
    schedule = build_schedule(seed, tok)
    timed, probes, violations, failures = [], [], [], []
    for i, req in enumerate(schedule):
        res = stream_completion(host, port, model, req)
        if req.kind == "warmup":
            continue
        if req.kind == "timed":
            m = measure_timed(res, tok)
            violations += m["violations"]
            timed.append(m)
            if "tps" in m:
                log(f"[{i}] timed ttft={m['ttft_ms']:.1f}ms tps={m['tps']:.1f}")
        else:
            ok = res.status == 200 and grade(req, res.text)
            probes.append({"kind": req.kind, "ok": ok})
            if not ok and len(failures) < 12:
                failures.append({"kind": req.kind, "expected": req.answer, "got": res.text[:160]})
            if res.status != 200:
                violations.append(f"probe http status={res.status} error={res.error}")

    good = [m for m in timed if "tps" in m]
    by_kind = {}
    for p in probes:
        by_kind.setdefault(p["kind"], []).append(p["ok"])
    if len(good) != config.TIMED_REQUESTS:
        violations.append(f"only {len(good)}/{config.TIMED_REQUESTS} timed requests measured")
    return {
        "model_id": model,
        "ttft_ms": statistics.median(m["ttft_ms"] for m in good) if good else None,
        "tps": statistics.median(m["tps"] for m in good) if good else None,
        "compress_ratio": statistics.median(m["compress_ratio"] for m in good) if good else None,
        "probe_correct": sum(p["ok"] for p in probes),
        "probe_total": len(probes),
        "probe_by_kind": {k: f"{sum(v)}/{len(v)}" for k, v in sorted(by_kind.items())},
        "probe_failures": failures,
        "timed": [{k: v for k, v in m.items() if k != "violations"} for m in timed],
        "violations": violations,
    }
