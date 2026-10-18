# GLM-5.3-Flash speedrun

An optimization loop for **single-user latency** of [GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash)
(320B total / 18B active, MIT) served from NVIDIA's NVFP4 checkpoint on **one Modal B300**.

Two axes: **decode tok/s** (maximize) and **TTFT** (minimize). An agent makes one small edit to
`candidate/`, runs the frozen benchmark on Modal, and the edit is kept or reverted automatically.

**Dashboard:** [`docs/index.html`](docs/index.html) (GitHub Pages: see repo About link).

## Score

```
score = 100 · (tps / tps_baseline)^(2/3) · (ttft_baseline / ttft)^(1/3)     baseline = 100
```

An experiment is **KEEP** only if all hold:

1. The run is valid (no integrity violations, see below).
2. Probe accuracy ≥ baseline accuracy − 2 standard errors (two-proportion, Agresti–Coull).
   Always measured against the **baseline**, never the current best, so quality can't ratchet down.
3. tok/s regresses no more than **5%** and TTFT no more than **50%** vs the current best.
   Decode is weighted 2× over TTFT: a decode win that costs some TTFT is kept, and TTFT is knocked
   down in later experiments. The 50% cap stops "buffer tokens, then burst" from gaming tok/s.
4. Score beats the current best by more than `max(1%, 2σ)`, where σ is the run-to-run score noise
   measured by the baseline runs (separate containers).
5. Steps 1–4 still hold after a **second confirmation run** (winner's-curse guard); the two runs are pooled.

Otherwise the change is reverted with `git checkout`, and the attempt (patch, metrics, reasons)
is still committed to `results/`.

## Workload

Per run (fresh random seed drawn **inside** the GPU container):

| Part | Count | Shape | Purpose |
|---|---|---|---|
| Warmup | 2 | 2048-token prompt → 512 tokens | not scored |
| Timed | 8 | 2048-token literary passage + "continue the story" → exactly 512 tokens (`ignore_eos`) | median TTFT, median decode tok/s |
| Probes | 96 | needle-sum, 2-digit arithmetic, sort, reverse; ≤48 tokens; exact-match graded | quality gate |

All requests are batch 1, sequential, greedy (`temperature=0`), raw `/v1/completions` with the
GLM chat format and an empty `<think></think>` block. Timed requests are shuffled among probes.

- **TTFT** = `max_{i<16}(t_i − i·g)`, where `t_i` is the arrival of streamed chunk *i* and `g` is the median
  inter-chunk gap. For an honest stream this equals the first-chunk time. A server that emits a guessed
  token before prefill finishes gets the prefill charged back to TTFT.
- **tok/s** = `(min(N, 512) − n_first) / (t_last − t_first)`, where `N` is the output re-tokenized by the
  client with the pinned tokenizer. Server-reported usage is ignored.

## Rules

- **Editable:** `candidate/` only. That covers the engine, its version, flags, patches, kernels,
  speculative decoding, other quantization recipes built from the pinned weights, and the image.
- **Frozen:** `harness/` is sealed. `SEAL` holds its hash history (append-only; last line is current), and every signed result embeds the
  harness hash that produced it. `speedrun.py` and `tests/` are frozen by policy: `run` refuses
  any uncommitted change outside `candidate/`, so edits to either show up in git history.
- **Fixed hardware:** 1× B300, checked with `nvidia-smi` inside the container.
- **Fixed model:** `nvidia/GLM-5.3-Flash-NVFP4@da920bb`, on a read-only volume. Extra repos in
  `candidate/extra_models.txt` may serve **only** as speculative-decoding drafts.
- **Forbidden:** special-casing prompt contents, caching or precomputing responses, or anything that
  changes output semantics beyond the quality gate. Every patch is public in `results/patches/`.

## Anti-cheat

| Attack | Defense | Test |
|---|---|---|
| Edit the benchmark | `SEAL` hash, checked before launch; harness hash embedded in the signed record and re-checked after the run | `test_seal_matches_harness` |
| Forge or alter results | HMAC-SHA256 signature with a Modal Secret key that nobody has seen; `speedrun.py verify` re-checks every record | `test_signature_roundtrip_and_tamper` |
| Server tampers with the client | Server runs as unprivileged uid 1500; harness, bench deps and `/candidate` are read-only; result goes to a root-only `0700` dir; key popped from the env before launch | — |
| Serve a smaller or different model | Runtime `block_network=True`; weights only from a read-only pinned volume; filesystem scan for >100 MB weight files outside `/models` | `test_foreign_weight_scan` |
| Cache or precompute answers | Fresh 63-bit seed per run generated in-container; nonce at the start of every prompt | `test_schedule_is_deterministic_per_seed_and_differs_across_seeds` |
| Fake an early first token | Effective-TTFT lookback over 16 chunks | `test_fake_first_token_is_charged_to_ttft` |
| Emit fewer tokens / stop early | `finish_reason` must be `length`; client re-tokenized count within ±5% of 512 | `test_mechanical_cheats_invalidate[short/early_eos]` |
| Pad text to inflate token counts | Count capped at 512; >5% over is a violation | `test_mechanical_cheats_invalidate[inflate]` |
| Cheap filler after a real start | Median zlib ratio of timed outputs ≥ 0.7× baseline | `test_filler_output_is_rejected` |
| Lossy speedups (aggressive quant, layer skipping) | 96 graded probes per run vs baseline accuracy | `test_wrong_answers_fail_quality` |
| Buffer output to game tok/s | TTFT weight + 50% TTFT cap (buffering D ms gains ≈D/3900 on decode, loses ≈D/150 on TTFT) | `test_burst_streaming_trips_ttft_guardrail` |
| Lucky noise counted as a win | Keep threshold ≥ 2σ of measured noise, plus a confirmation run | `test_honest_rerun_is_not_a_keep` |

**Residual risks.** The candidate controls the base image, including its `python3`, which also runs
the frozen client. A malicious image could patch the interpreter. Code that parses probe prompts
would also pass the gates. Both are blatant in a diff, and every diff is public.

## Usage

```bash
uv sync
uv run pytest                                    # harness tests (no GPU)
uv run speedrun.py download                      # one-time: 204 GB -> Modal volume
uv run speedrun.py baseline -n 3                 # sets baseline + noise floor
uv run speedrun.py run -m "enable cuda graphs bs=1"
uv run speedrun.py status
uv run speedrun.py verify                        # re-check all signatures on Modal
```

Each experiment costs about **$0.20–0.35**, dominated by weight load plus engine startup at
$7.10/hr on B300. JIT caches persist in a Modal volume across runs. Spend is tracked in
`results/runs.jsonl` and capped at `BUDGET_USD` (default $30). These are estimates; the Modal
dashboard has the actual bill.
