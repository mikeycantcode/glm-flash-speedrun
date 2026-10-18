"""Unit tests: workload determinism, grading, scoring math, integrity."""

import os
import random
from pathlib import Path

import pytest

from harness import config, integrity, scoring, workload
from tests.fakes import ToyTokenizer

ROOT = Path(__file__).resolve().parent.parent


def test_schedule_is_deterministic_per_seed_and_differs_across_seeds():
    a = workload.build_schedule(42, ToyTokenizer())
    b = workload.build_schedule(42, ToyTokenizer())
    c = workload.build_schedule(43, ToyTokenizer())
    assert [r.prompt for r in a] == [r.prompt for r in b]
    assert {r.prompt for r in a}.isdisjoint({r.prompt for r in c})  # nonces defeat prefix/response caches


def test_schedule_shape():
    s = workload.build_schedule(7, ToyTokenizer())
    kinds = [r.kind for r in s]
    assert kinds[: config.WARMUP_REQUESTS] == ["warmup"] * config.WARMUP_REQUESTS
    assert kinds.count("timed") == config.TIMED_REQUESTS
    for k in workload.PROBE_KINDS:
        assert kinds.count(k) == config.PROBES_PER_KIND
    assert all(r.prompt.startswith(workload.PROMPT_PREFIX) and r.prompt.endswith(workload.PROMPT_SUFFIX) for r in s)


def test_timed_prompts_hit_token_target():
    tok = ToyTokenizer()
    for r in workload.build_schedule(3, tok):
        if r.kind in ("timed", "warmup"):
            assert abs(len(tok.encode(r.prompt)) - config.PROMPT_TOKENS) <= config.PROMPT_TOKENS_TOLERANCE
            assert r.ignore_eos and r.max_tokens == config.OUTPUT_TOKENS


def test_probe_answers_are_correct():
    rng = random.Random(0)
    words = workload.load_words()
    for _ in range(50):
        r = workload.probe_request(rng, "arith", words)
        a, b, c = map(int, __import__("re").search(r"Compute (\d+) \* (\d+) \+ (\d+)", r.prompt).groups())
        assert r.answer == str(a * b + c)


@pytest.mark.parametrize("kind,answer,output,ok", [
    ("arith", "1234", "1234", True),
    ("arith", "1234", "1,234\nbecause...", True),
    ("arith", "1234", "45 * 22 + 244 = 1234", True),
    ("arith", "1234", "1234 is wrong, it is 1243", False),
    ("arith", "1234", "The answer is 1234.", True),
    ("arith", "1234", "1243", False),
    ("arith", "1234", "", False),
    ("sort", "apple, bread, crane", "apple, bread, crane", True),
    ("sort", "apple, bread, crane", "Apple, Bread, Crane.", True),
    ("sort", "apple, bread, crane", "bread, apple, crane", False),
])
def test_grading(kind, answer, output, ok):
    req = workload.Request(kind, "", 8, False, answer)
    assert workload.grade(req, output) is ok


BASE = {"tps": 200.0, "ttft_ms": 100.0, "compress_ratio": 0.4, "probe_correct": 270, "probe_total": 288,
        "violations": [], "score_sigma": 0.004}


def cand(**kw):
    m = {"tps": 200.0, "ttft_ms": 100.0, "compress_ratio": 0.4, "probe_correct": 90, "probe_total": 96, "violations": []}
    m.update(kw)
    return m


def test_score_is_100_at_baseline_and_geometric():
    assert scoring.score(BASE, BASE) == pytest.approx(100)
    assert scoring.score(cand(tps=400), BASE) == pytest.approx(100 * 2**0.5)
    assert scoring.score(cand(tps=400, ttft_ms=200), BASE) == pytest.approx(100)


def test_keep_requires_beating_noise():
    assert scoring.decide(cand(tps=201), BASE, BASE)[0] == "REVERT"  # +0.25% score < 1% threshold
    assert scoring.decide(cand(tps=220), BASE, BASE)[0] == "KEEP"


def test_guardrail_blocks_trading_one_axis_away():
    # +40% tps but TTFT +10%: geo-mean improves, guardrail still rejects
    d, reasons = scoring.decide(cand(tps=280, ttft_ms=110), BASE, BASE)
    assert d == "REVERT" and any("guardrail" in r for r in reasons)


def test_quality_gate_tolerates_noise_but_not_damage():
    assert scoring.decide(cand(tps=260, probe_correct=88), BASE, BASE)[0] == "KEEP"  # 91.7% vs 93.8%
    d, reasons = scoring.decide(cand(tps=260, probe_correct=75), BASE, BASE)  # 78% vs 93.8%
    assert d == "REVERT" and any("quality" in r for r in reasons)


def test_quality_measured_against_baseline_not_best():
    """No ratchet: a lucky-accuracy best can't tighten the gate, a degraded best can't loosen it."""
    best = cand(tps=300, probe_correct=60)
    d, reasons = scoring.decide(cand(tps=330, probe_correct=60), best, BASE)
    assert d == "REVERT" and any("quality" in r for r in reasons)


def test_violations_make_run_invalid():
    assert scoring.decide(cand(tps=999, violations=["x"]), BASE, BASE)[0] == "INVALID"


def test_signature_roundtrip_and_tamper():
    rec = {"tps": 200.0, "seed": 5}
    sig = integrity.sign(rec, b"k")
    assert integrity.verify(rec, sig, b"k")
    assert not integrity.verify({**rec, "tps": 201.0}, sig, b"k")
    assert not integrity.verify(rec, sig, b"other")


def test_foreign_weight_scan(tmp_path):
    allowed = tmp_path / "models"
    allowed.mkdir()
    (tmp_path / "small.safetensors").write_bytes(b"0" * 10)
    big = tmp_path / "sneaky.safetensors"
    with open(big, "wb") as f:
        f.truncate(integrity.WEIGHT_MIN_BYTES)
    with open(allowed / "ok.safetensors", "wb") as f:
        f.truncate(integrity.WEIGHT_MIN_BYTES)
    assert integrity.scan_foreign_weights([str(tmp_path)], [str(allowed)]) == [str(big)]
    # The same allowed dir reached through another path (bind mount / symlink) is still allowed.
    (tmp_path / "mnt").symlink_to(allowed, target_is_directory=True)
    assert integrity.scan_foreign_weights([str(tmp_path / "mnt")], [str(allowed)]) == []


def test_seal_matches_harness():
    seal = ROOT / "SEAL"
    if not seal.exists():
        pytest.skip("not sealed yet")
    assert seal.read_text().strip() == integrity.harness_hash(), "harness/ changed after sealing"
