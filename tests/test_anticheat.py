"""End-to-end: the real client + scoring against a fake server in honest and cheating modes."""

import pytest

from harness import client, config, scoring
from tests.fakes import FakeServer, ToyTokenizer


@pytest.fixture(autouse=True)
def small_workload(monkeypatch):
    monkeypatch.setattr(config, "PROMPT_TOKENS", 256)
    monkeypatch.setattr(config, "OUTPUT_TOKENS", 128)
    monkeypatch.setattr(config, "WARMUP_REQUESTS", 1)
    monkeypatch.setattr(config, "TIMED_REQUESTS", 4)
    monkeypatch.setattr(config, "PROBES_PER_KIND", 4)


def bench(mode: str, seed: int = 1) -> dict:
    srv = FakeServer(mode)
    try:
        return client.run_benchmark("127.0.0.1", srv.port, ToyTokenizer(), seed, log=lambda _m: None)
    finally:
        srv.close()


@pytest.fixture(scope="module")
def baseline():
    # Module-scoped fixtures can't use the function-scoped monkeypatch.
    mp = pytest.MonkeyPatch()
    for k, v in dict(PROMPT_TOKENS=256, OUTPUT_TOKENS=128, WARMUP_REQUESTS=1, TIMED_REQUESTS=4, PROBES_PER_KIND=4).items():
        mp.setattr(config, k, v)
    runs = [bench("honest", seed) for seed in (1, 2, 3)]
    mp.undo()
    return scoring.baseline_stats(runs)


def test_honest_run_is_valid_and_accurate():
    r = bench("honest")
    assert r["violations"] == []
    assert r["probe_correct"] == r["probe_total"] == 16
    assert 20 <= r["ttft_ms"] <= 200  # prefill_s = 30ms
    assert r["tps"] > 100


def test_fake_first_token_is_charged_to_ttft():
    r = bench("fake_first")
    raw = [t["ttft_raw_ms"] for t in r["timed"]]
    assert max(raw) < 15  # the lie: first chunk arrives instantly
    assert r["ttft_ms"] >= 25  # but effective TTFT still includes the 30ms prefill


@pytest.mark.parametrize("mode,needle", [
    ("short", "re-tokenizes"),
    ("early_eos", "finish_reason"),
    ("inflate", "re-tokenizes"),
    ("http_error", "http status"),
])
def test_mechanical_cheats_invalidate(mode, needle, baseline):
    r = bench(mode)
    assert any(needle in v for v in r["violations"]), r["violations"]
    m = scoring.merge([r]) if r["tps"] else {"violations": r["violations"]}
    decision, _ = scoring.decide(m, baseline, baseline) if r["tps"] else ("INVALID", [])
    assert decision == "INVALID"


def test_filler_output_is_rejected(baseline):
    r = bench("filler")
    decision, reasons = scoring.decide(scoring.merge([r]), baseline, baseline)
    assert decision == "REVERT"
    assert any("degenerate" in x for x in reasons)


def test_wrong_answers_fail_quality(baseline):
    r = bench("wrong")
    decision, reasons = scoring.decide(scoring.merge([r]), baseline, baseline)
    assert decision == "REVERT"
    assert any("quality" in x for x in reasons)


def test_burst_streaming_trips_ttft_guardrail(baseline):
    r = bench("burst")
    decision, reasons = scoring.decide(scoring.merge([r]), baseline, baseline)
    assert decision == "REVERT"
    assert any("ttft" in x for x in reasons)


def test_slower_server_is_reverted(baseline):
    decision, _ = scoring.decide(scoring.merge([bench("slow")]), baseline, baseline)
    assert decision == "REVERT"


def test_honest_rerun_is_not_a_keep(baseline):
    """Same config re-measured must not count as an improvement (noise floor works)."""
    decision, reasons = scoring.decide(scoring.merge([bench("honest", 9)]), baseline, baseline)
    assert decision == "REVERT", reasons
