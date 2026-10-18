"""Score and keep/revert rule.

score = 100 * sqrt((tps / tps_base) * (ttft_base / ttft))   (baseline = 100)

KEEP iff the run is valid, quality holds vs the baseline, neither axis regresses
more than GUARDRAIL vs the current best, and the score beats the best by more
than max(MIN_KEEP_DELTA, 2 * baseline noise).
"""

from __future__ import annotations

import math
import statistics

from harness import config


def merge(runs: list[dict]) -> dict:
    """Pool several runs of the same config into one measurement."""
    return {
        "tps": statistics.mean(r["tps"] for r in runs),
        "ttft_ms": statistics.mean(r["ttft_ms"] for r in runs),
        "compress_ratio": min(r["compress_ratio"] for r in runs),
        "probe_correct": sum(r["probe_correct"] for r in runs),
        "probe_total": sum(r["probe_total"] for r in runs),
        "violations": [v for r in runs for v in r["violations"]],
        "n_runs": len(runs),
    }


def score(m: dict, base: dict) -> float:
    return 100 * math.sqrt((m["tps"] / base["tps"]) * (base["ttft_ms"] / m["ttft_ms"]))


def baseline_stats(runs: list[dict]) -> dict:
    base = merge(runs)
    scores = [score(r, base) / 100 for r in runs]
    base["score_sigma"] = statistics.stdev(scores) if len(scores) > 1 else 0.0
    base["tps_sigma"] = statistics.stdev(r["tps"] for r in runs) / base["tps"] if len(runs) > 1 else 0.0
    base["ttft_sigma"] = statistics.stdev(r["ttft_ms"] for r in runs) / base["ttft_ms"] if len(runs) > 1 else 0.0
    return base


def quality_tolerance(base: dict, n_cand: int) -> float:
    """Two standard errors of a two-proportion difference (Agresti-Coull smoothed)."""
    p = (base["probe_correct"] + 2) / (base["probe_total"] + 4)
    return 2 * math.sqrt(p * (1 - p) * (1 / n_cand + 1 / base["probe_total"]))


def keep_delta(base: dict) -> float:
    return max(config.MIN_KEEP_DELTA, 2 * base["score_sigma"])


def decide(cand: dict, best: dict, base: dict) -> tuple[str, list[str]]:
    """Return ("KEEP" | "REVERT" | "INVALID", reasons)."""
    if cand["violations"]:
        return "INVALID", cand["violations"][:10]

    reasons = []
    acc_c = cand["probe_correct"] / cand["probe_total"]
    acc_b = base["probe_correct"] / base["probe_total"]
    tol = quality_tolerance(base, cand["probe_total"])
    if acc_c < acc_b - tol:
        reasons.append(f"quality: accuracy {acc_c:.3f} < baseline {acc_b:.3f} - {tol:.3f}")
    if cand["compress_ratio"] < config.COMPRESS_RATIO_FLOOR * base["compress_ratio"]:
        reasons.append(
            f"degenerate output: compress ratio {cand['compress_ratio']:.3f} < "
            f"{config.COMPRESS_RATIO_FLOOR} x baseline {base['compress_ratio']:.3f}"
        )
    if cand["tps"] < best["tps"] * (1 - config.GUARDRAIL):
        reasons.append(f"guardrail: tps {cand['tps']:.1f} < best {best['tps']:.1f} - {config.GUARDRAIL:.0%}")
    if cand["ttft_ms"] > best["ttft_ms"] * (1 + config.GUARDRAIL):
        reasons.append(f"guardrail: ttft {cand['ttft_ms']:.1f}ms > best {best['ttft_ms']:.1f}ms + {config.GUARDRAIL:.0%}")

    s_c, s_b, delta = score(cand, base), score(best, base), keep_delta(base)
    if s_c <= s_b * (1 + delta):
        reasons.append(f"score {s_c:.2f} does not beat best {s_b:.2f} by >{delta:.1%}")
    if reasons:
        return "REVERT", reasons
    return "KEEP", [f"score {s_b:.2f} -> {s_c:.2f}"]
