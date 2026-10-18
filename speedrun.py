"""speedrun CLI: one experiment = edit candidate/, run, keep or revert.

  uv run speedrun.py download          # one-time: weights -> Modal volume
  uv run speedrun.py baseline [-n 3]   # measure the unmodified candidate, set noise floor
  uv run speedrun.py run -m "what I changed"
  uv run speedrun.py status | verify | dashboard
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from harness import config, scoring
from harness.integrity import harness_hash, tree_hash

ROOT = Path(__file__).resolve().parent
SEAL = ROOT / "SEAL"
RUNS = ROOT / "results" / "runs.jsonl"
PATCHES = ROOT / "results" / "patches"
DATA_JS = ROOT / "docs" / "data.js"
OVERHEAD_S = 30  # container start + image load, not visible from inside


def sh(*args: str, check: bool = True) -> str:
    return subprocess.run(args, cwd=ROOT, check=check, capture_output=True, text=True).stdout.strip()


def die(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(1)


def load_runs() -> list[dict]:
    return [json.loads(line) for line in RUNS.read_text().splitlines() if line.strip()] if RUNS.exists() else []


def append_run(entry: dict) -> None:
    RUNS.parent.mkdir(parents=True, exist_ok=True)
    with RUNS.open("a") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")


def seals() -> list[str]:
    """SEAL is append-only: every harness version ever sealed, current one last."""
    return SEAL.read_text().split() if SEAL.exists() else []


def require_sealed() -> str:
    if not SEAL.exists():
        die("harness not sealed (run `speedrun.py seal` once the env is final)")
    sealed = seals()[-1]
    if harness_hash() != sealed:
        die("harness/ does not match SEAL: the benchmark was modified")
    return sealed


def metrics_of(item: dict, sealed: str) -> dict:
    rec = item["record"]
    violations = list(rec.get("violations", []))
    if not item.get("signature"):
        violations.append("unsigned record")
    if rec.get("harness_hash") != sealed:
        violations.append("record harness_hash != SEAL")
    if rec.get("candidate_hash") != tree_hash(ROOT / "candidate"):
        violations.append("record candidate_hash != local candidate/")
    return {
        "tps": rec.get("tps"),
        "ttft_ms": rec.get("ttft_ms"),
        "compress_ratio": rec.get("compress_ratio"),
        "probe_correct": rec.get("probe_correct", 0),
        "probe_total": rec.get("probe_total", 0),
        "violations": violations,
    }


def cost_of(rec: dict) -> float:
    return round((rec.get("container_s", 0) + OVERHEAD_S) * config.USD_PER_S, 4)


def spent(runs: list[dict]) -> float:
    return sum(r.get("cost_usd", 0) for r in runs)


def baseline_of(runs: list[dict]) -> dict | None:
    """Pool valid baseline runs of the most recent baseline candidate only."""
    bl = [r for r in runs if r["kind"] == "baseline"]
    if not bl:
        return None
    current = bl[-1]["record"].get("candidate_hash")
    base = [r["metrics"] for r in bl if r["record"].get("candidate_hash") == current and not r["metrics"]["violations"]]
    return scoring.baseline_stats(base) if len(base) >= 2 else None


def best_of(runs: list[dict], base: dict) -> dict:
    kept = [r for r in runs if r["kind"] == "experiment" and r["decision"] == "KEEP"]
    return kept[-1]["merged"] if kept else base


def ensure_derived() -> None:
    """Build (or reuse) the derived checkpoint for candidate/convert.py. CPU only."""
    script = ROOT / "candidate" / "convert.py"
    if not script.exists():
        return
    import modal

    from harness.modal_app import app, convert

    with modal.enable_output(), app.run():
        print(convert.remote(script.read_text()))


def remote_bench(n: int) -> list[dict]:
    import modal

    from harness.modal_app import app, bench

    with modal.enable_output(), app.run():
        return list(bench.map(range(n)))


def next_id(runs: list[dict]) -> int:
    return 1 + max((r["id"] for r in runs if r["kind"] == "experiment"), default=0)


def git_changed() -> list[str]:
    # Not sh(): its .strip() would eat the leading status column of the first line.
    out = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                         cwd=ROOT, check=True, capture_output=True, text=True).stdout
    return [line[3:] for line in out.splitlines() if line.strip()]


def commit_and_push(paths: list[str], message: str) -> None:
    sh("git", "add", "--", *paths)
    sh("git", "commit", "-q", "-m", message)
    if sh("git", "remote", check=False):
        push = subprocess.run(["git", "push", "-q"], cwd=ROOT, capture_output=True, text=True)
        if push.returncode != 0:
            print(f"warning: git push failed; dashboard not updated:\n{push.stderr.strip()[-400:]}", file=sys.stderr)


# ---------------------------------------------------------------- commands


def cmd_seal(_args) -> None:
    h = harness_hash()
    if h not in seals():
        with SEAL.open("a") as f:
            f.write(h + "\n")
    print(f"sealed harness {h} ({len(seals())} versions)")


def cmd_download(_args) -> None:
    import modal

    from harness.modal_app import app, download, extra_models

    with modal.enable_output(), app.run():
        for line in download.remote([(config.MODEL_REPO, config.MODEL_REVISION), *extra_models()]):
            print(line)


def cmd_baseline(args) -> None:
    sealed = require_sealed()
    if any(p.startswith("candidate/") for p in git_changed()):
        die("candidate/ has uncommitted changes; baseline must run on the committed candidate")
    runs = load_runs()
    t0 = time.time()
    items = remote_bench(args.n)
    print(f"{args.n} baseline runs in {time.time() - t0:.0f}s")
    for item in items:
        m = metrics_of(item, sealed)
        entry = {"kind": "baseline", "id": 0, "ts": item["record"].get("started_at"), "metrics": m,
                 "cost_usd": cost_of(item["record"]), "record": item["record"], "signature": item["signature"]}
        append_run(entry)
        print(f"  tps={m['tps']} ttft_ms={m['ttft_ms']} acc={m['probe_correct']}/{m['probe_total']} "
              f"startup={item['record'].get('startup_s')}s violations={m['violations'][:3]}")
    base = baseline_of(load_runs())
    if base:
        print(f"baseline: tps={base['tps']:.1f} (sigma {base['tps_sigma']:.1%}) "
              f"ttft={base['ttft_ms']:.1f}ms (sigma {base['ttft_sigma']:.1%}) "
              f"score sigma {base['score_sigma']:.1%} -> keep threshold {scoring.keep_delta(base):.1%}")
    write_dashboard()
    commit_and_push(["results", "docs"], f"baseline: {args.n} runs")
    print(f"spent so far: ${spent(load_runs()):.2f} / ${config.BUDGET_USD:.2f}")


def cmd_run(args) -> None:
    sealed = require_sealed()
    runs = load_runs()
    base = baseline_of(runs)
    if not base:
        die("no baseline yet (run `speedrun.py baseline`)")
    changed = git_changed()
    outside = [p for p in changed if not p.startswith(("candidate/", "results/", "docs/"))]
    if outside:
        die(f"only candidate/ may change during experiments; also changed: {outside}")
    if not any(p.startswith("candidate/") for p in changed):
        die("no change in candidate/")
    if spent(runs) >= config.BUDGET_USD and not args.force:
        die(f"budget exhausted: ${spent(runs):.2f} >= ${config.BUDGET_USD:.2f}")

    exp_id = next_id(runs)
    sh("git", "add", "-N", "candidate")
    patch = sh("git", "diff", "HEAD", "--", "candidate")
    PATCHES.mkdir(parents=True, exist_ok=True)
    (PATCHES / f"{exp_id:04d}.diff").write_text(patch + "\n")
    best = best_of(runs, base)

    ensure_derived()
    items = remote_bench(1)
    measured = [metrics_of(items[0], sealed)]
    decision, reasons = scoring.decide(scoring.merge(measured), best, base)
    if decision == "KEEP":  # confirm with a second container before accepting
        print("candidate beat best; confirming with a second run")
        items += remote_bench(1)
        measured.append(metrics_of(items[1], sealed))
        decision, reasons = scoring.decide(scoring.merge(measured), best, base)

    merged = scoring.merge(measured)
    score = scoring.score(merged, base) if not merged["violations"] else None
    entry = {
        "kind": "experiment", "id": exp_id, "message": args.m, "ts": items[0]["record"].get("started_at"),
        "decision": decision, "reasons": reasons, "score": score, "best_score_before": scoring.score(best, base),
        "merged": merged, "patch": f"results/patches/{exp_id:04d}.diff",
        "cost_usd": sum(cost_of(i["record"]) for i in items),
        "startup_s": items[0]["record"].get("startup_s"),
        "items": [{"record": i["record"], "signature": i["signature"]} for i in items],
    }
    append_run(entry)
    write_dashboard()

    title = f"exp {exp_id:04d} {decision}: {args.m}" + (f" (score {score:.2f})" if score else "")
    if decision == "KEEP":
        commit_and_push(["candidate", "results", "docs"], title)
    else:
        sh("git", "checkout", "HEAD", "--", "candidate")
        sh("git", "clean", "-fdq", "candidate")
        commit_and_push(["results", "docs"], title)

    print(f"\n{title}")
    for r in reasons:
        print(f"  - {r}")
    if score:
        print(f"  tps={merged['tps']:.1f} ttft={merged['ttft_ms']:.1f}ms "
              f"acc={merged['probe_correct']}/{merged['probe_total']} startup={entry['startup_s']}s")
    print(f"  cost ${entry['cost_usd']:.2f}, total ${spent(load_runs()):.2f} / ${config.BUDGET_USD:.2f}")


def cmd_status(_args) -> None:
    runs = load_runs()
    base = baseline_of(runs)
    if not base:
        print("no baseline yet")
        return
    best = best_of(runs, base)
    exps = [r for r in runs if r["kind"] == "experiment"]
    print(f"baseline tps={base['tps']:.1f} ttft={base['ttft_ms']:.1f}ms; keep threshold {scoring.keep_delta(base):.1%}")
    print(f"best     tps={best['tps']:.1f} ttft={best['ttft_ms']:.1f}ms score={scoring.score(best, base):.2f}")
    print(f"experiments: {len(exps)} ({sum(r['decision'] == 'KEEP' for r in exps)} kept); "
          f"spent ${spent(runs):.2f} / ${config.BUDGET_USD:.2f}")
    for r in exps[-10:]:
        s = f"{r['score']:.2f}" if r["score"] else "  -  "
        print(f"  {r['id']:04d} {r['decision']:7s} {s:>7s}  {r['message']}")


def cmd_verify(_args) -> None:
    import modal

    from harness.modal_app import app, verify

    sealed = set(seals())
    runs = load_runs()
    items = [{"record": r["record"], "signature": r["signature"]} for r in runs if r["kind"] == "baseline"]
    items += [i for r in runs if r["kind"] == "experiment" for i in r["items"]]
    with modal.enable_output(), app.run():
        ok = verify.remote(items)
    bad_sig = sum(not x for x in ok)
    bad_seal = sum(i["record"].get("harness_hash") not in sealed for i in items)
    print(f"{len(items)} records: {bad_sig} bad signatures, {bad_seal} with a harness_hash not in SEAL")
    sys.exit(1 if bad_sig or bad_seal else 0)


def write_dashboard() -> None:
    runs = load_runs()
    base = baseline_of(runs)
    # Raw config value (no url.insteadOf rewrite), with any credentials stripped: this file is public.
    repo = re.sub(r"//[^/@]+@", "//", sh("git", "config", "--get", "remote.origin.url", check=False)).removesuffix(".git")
    rows = []
    for r in runs:
        m = r["metrics"] if r["kind"] == "baseline" else r["merged"]
        valid = not m["violations"]
        rows.append({
            "kind": r["kind"], "id": r["id"], "ts": r.get("ts"), "message": r.get("message", "baseline"),
            "decision": r.get("decision", "BASELINE" if valid else "INVALID"),
            "reasons": r.get("reasons", m["violations"][:3]),
            "score": scoring.score(m, base) if base and valid else None,
            "tps": m["tps"] if valid else None, "ttft_ms": m["ttft_ms"] if valid else None,
            "accuracy": m["probe_correct"] / m["probe_total"] if m["probe_total"] else None,
            "cost_usd": r.get("cost_usd", 0), "patch": r.get("patch"),
            "startup_s": r.get("startup_s", r.get("record", {}).get("startup_s")),
        })
    data = {
        "generated_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()), "repo": repo,
        "budget_usd": config.BUDGET_USD, "spent_usd": spent(runs),
        "keep_threshold": scoring.keep_delta(base) if base else None,
        "baseline": {"tps": base["tps"], "ttft_ms": base["ttft_ms"]} if base else None,
        "runs": rows,
    }
    DATA_JS.parent.mkdir(parents=True, exist_ok=True)
    DATA_JS.write_text("window.SPEEDRUN = " + json.dumps(data, indent=1) + ";\n")


def cmd_dashboard(_args) -> None:
    write_dashboard()
    print(f"wrote {DATA_JS.relative_to(ROOT)}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("seal").set_defaults(fn=cmd_seal)
    sub.add_parser("download").set_defaults(fn=cmd_download)
    b = sub.add_parser("baseline")
    b.add_argument("-n", type=int, default=3)
    b.set_defaults(fn=cmd_baseline)
    r = sub.add_parser("run")
    r.add_argument("-m", required=True, help="one-line description of the change")
    r.add_argument("--force", action="store_true", help="run even if over budget")
    r.set_defaults(fn=cmd_run)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    sub.add_parser("verify").set_defaults(fn=cmd_verify)
    sub.add_parser("dashboard").set_defaults(fn=cmd_dashboard)
    args = p.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
