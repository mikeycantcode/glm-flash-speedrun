window.SPEEDRUN = {
 "generated_at": "2026-10-20 01:20 UTC",
 "repo": "https://github.com/mikeycantcode/glm-flash-speedrun",
 "budget_usd": 30.0,
 "spent_usd": 23.145500000000002,
 "keep_threshold": 0.01,
 "baseline": {
  "tps": 130.64947461755435,
  "ttft_ms": 151.25697616666875
 },
 "runs": [
  {
   "kind": "baseline",
   "id": 0,
   "ts": "2026-10-18T19:53:39Z",
   "message": "baseline",
   "decision": "INVALID",
   "reasons": [
    "RuntimeError: server process exited before becoming ready"
   ],
   "score": null,
   "tps": null,
   "ttft_ms": null,
   "accuracy": null,
   "cost_usd": 0.0991,
   "patch": null,
   "startup_s": null
  },
  {
   "kind": "baseline",
   "id": 0,
   "ts": "2026-10-18T19:54:51Z",
   "message": "baseline",
   "decision": "BASELINE",
   "reasons": [],
   "score": 94.911782550293,
   "tps": 130.25865107348352,
   "ttft_ms": 175.8542390000457,
   "accuracy": 0.8229166666666666,
   "cost_usd": 2.4844,
   "patch": null,
   "startup_s": 970.87
  },
  {
   "kind": "baseline",
   "id": 0,
   "ts": "2026-10-18T20:15:13Z",
   "message": "baseline",
   "decision": "BASELINE",
   "reasons": [],
   "score": 99.80931419974262,
   "tps": 130.13959883121026,
   "ttft_ms": 150.94050249999214,
   "accuracy": 0.90625,
   "cost_usd": 0.9848,
   "patch": null,
   "startup_s": 309.12
  },
  {
   "kind": "baseline",
   "id": 0,
   "ts": "2026-10-18T20:15:13Z",
   "message": "baseline",
   "decision": "BASELINE",
   "reasons": [],
   "score": 100.20542691173827,
   "tps": 130.87959304730003,
   "ttft_ms": 150.85865200003923,
   "accuracy": 0.84375,
   "cost_usd": 0.9835,
   "patch": null,
   "startup_s": 309.35
  },
  {
   "kind": "baseline",
   "id": 0,
   "ts": "2026-10-18T20:15:13Z",
   "message": "baseline",
   "decision": "BASELINE",
   "reasons": [],
   "score": 99.98544766884898,
   "tps": 130.9292319741527,
   "ttft_ms": 151.97177399997486,
   "accuracy": 0.875,
   "cost_usd": 0.9802,
   "patch": null,
   "startup_s": 308.56
  },
  {
   "kind": "experiment",
   "id": 1,
   "ts": "2026-10-18T20:44:33Z",
   "message": "MTP self-speculation (EAGLE topk1, 3 steps) + flashinfer_trtllm MoE runner (recipe default on B300)",
   "decision": "REVERT",
   "reasons": [
    "guardrail: ttft 161.9ms > best 151.3ms + 5%"
   ],
   "score": 138.50183589502444,
   "tps": 220.30773378352035,
   "ttft_ms": 161.8799175000163,
   "accuracy": 0.8958333333333334,
   "cost_usd": 1.5578,
   "patch": "results/patches/0001.diff",
   "startup_s": 570.28
  },
  {
   "kind": "experiment",
   "id": 2,
   "ts": "2026-10-18T20:57:08Z",
   "message": "MTP 3/1/4 + trtllm MoE + ptx_kda KDA prefill (TTFT) + cutedsl DSA paged-MQA logits",
   "decision": "REVERT",
   "reasons": [
    "guardrail: ttft 171.3ms > best 151.3ms + 5%"
   ],
   "score": 137.7283931473986,
   "tps": 224.72895423179818,
   "ttft_ms": 171.2961880000421,
   "accuracy": 0.9166666666666666,
   "cost_usd": 1.8734,
   "patch": "results/patches/0002.diff",
   "startup_s": 448.03
  },
  {
   "kind": "experiment",
   "id": 3,
   "ts": "2026-10-18T22:44:36Z",
   "message": "MTP self-speculation (EAGLE topk1, 3 steps) + flashinfer_trtllm MoE [re-run under decode-weighted rule]",
   "decision": "KEEP",
   "reasons": [
    "score 100.00 -> 140.23"
   ],
   "score": 140.23353609804457,
   "tps": 220.34253956450544,
   "ttft_ms": 156.00593624999703,
   "accuracy": 0.8802083333333334,
   "cost_usd": 2.4402,
   "patch": "results/patches/0003.diff",
   "startup_s": 363.7
  },
  {
   "kind": "experiment",
   "id": 4,
   "ts": "2026-10-18T23:03:30Z",
   "message": "MTP 2 steps (was 3; accept len ~2.2) + fused KDA verify (triton verify backend)",
   "decision": "INVALID",
   "reasons": [
    "record harness_hash != SEAL"
   ],
   "score": null,
   "tps": null,
   "ttft_ms": null,
   "accuracy": 0.890625,
   "cost_usd": 2.067,
   "patch": "results/patches/0004.diff",
   "startup_s": 179.89
  },
  {
   "kind": "experiment",
   "id": 5,
   "ts": "2026-10-18T23:35:37Z",
   "message": "FP8 block requant of BF16 attention+shared experts (19.4->12.7 GB/fwd, modelopt_mixed) + MTP 2 steps + fused KDA verify",
   "decision": "INVALID",
   "reasons": [
    "RuntimeError: server process exited before becoming ready"
   ],
   "score": null,
   "tps": null,
   "ttft_ms": null,
   "accuracy": null,
   "cost_usd": 0.2524,
   "patch": "results/patches/0005.diff",
   "startup_s": null
  },
  {
   "kind": "experiment",
   "id": 6,
   "ts": "2026-10-19T23:28:15Z",
   "message": "FP8 block requant of BF16 attention+shared experts (19.4->12.7 GB/fwd, modelopt_mixed) + MTP 2 steps + fused KDA verify [retry: in-place convert]",
   "decision": "INVALID",
   "reasons": [
    "RuntimeError: server process exited before becoming ready"
   ],
   "score": null,
   "tps": null,
   "ttft_ms": null,
   "accuracy": null,
   "cost_usd": 0.1933,
   "patch": "results/patches/0006.diff",
   "startup_s": null
  },
  {
   "kind": "experiment",
   "id": 7,
   "ts": "2026-10-19T23:31:59Z",
   "message": "FP8 block requant of BF16 attention+shared experts (19.4->12.7 GB/fwd, modelopt_mixed) + MTP 2 steps + fused KDA verify [retry: readable derived files]",
   "decision": "REVERT",
   "reasons": [
    "score 137.90 does not beat best 140.23 by >1.0%"
   ],
   "score": 137.89554425835036,
   "tps": 236.1373828195251,
   "ttft_ms": 188.44250550000652,
   "accuracy": 0.9166666666666666,
   "cost_usd": 2.8948,
   "patch": "results/patches/0007.diff",
   "startup_s": 1158.54
  },
  {
   "kind": "experiment",
   "id": 8,
   "ts": "2026-10-19T23:54:31Z",
   "message": "FP8 requant + flashinfer_trtllm FP8 GEMM backend (low-latency) + metadata glue graph + MTP 2 steps + fused KDA verify",
   "decision": "REVERT",
   "reasons": [
    "score 136.71 does not beat best 140.23 by >1.0%"
   ],
   "score": 136.70796317482,
   "tps": 240.55684965995323,
   "ttft_ms": 200.70310699998117,
   "accuracy": 0.8645833333333334,
   "cost_usd": 3.0832,
   "patch": "results/patches/0008.diff",
   "startup_s": 867.09
  },
  {
   "kind": "experiment",
   "id": 9,
   "ts": "2026-10-20T00:18:32Z",
   "message": "MTP 2 steps + triton fused KDA verify + no radix cache + overlap plan stream (overhead trims on exp 3 base)",
   "decision": "KEEP",
   "reasons": [
    "score 140.23 -> 165.44"
   ],
   "score": 165.43869678801406,
   "tps": 230.9767927532819,
   "ttft_ms": 104.40600324994875,
   "accuracy": 0.84375,
   "cost_usd": 1.6987,
   "patch": "results/patches/0009.diff",
   "startup_s": 371.42
  },
  {
   "kind": "experiment",
   "id": 10,
   "ts": "2026-10-20T01:05:11Z",
   "message": "BF16 GEMMs via cuBLAS (--bf16-gemm-backend torch, drop CuTe-DSL TGV) + flashinfer DSA top-k",
   "decision": "REVERT",
   "reasons": [
    "score 165.46 does not beat best 165.44 by >1.0%"
   ],
   "score": 165.4646401732496,
   "tps": 234.04534555896979,
   "ttft_ms": 107.14810600016733,
   "accuracy": 0.8645833333333334,
   "cost_usd": 0.6664,
   "patch": "results/patches/0010.diff",
   "startup_s": 208.64
  },
  {
   "kind": "experiment",
   "id": 11,
   "ts": "2026-10-20T01:12:39Z",
   "message": "DFlash block-diffusion drafter (modal-labs, block 8, unquantized draft) replacing MTP",
   "decision": "INVALID",
   "reasons": [
    "RuntimeError: server process exited before becoming ready"
   ],
   "score": null,
   "tps": null,
   "ttft_ms": null,
   "accuracy": null,
   "cost_usd": 0.2968,
   "patch": "results/patches/0011.diff",
   "startup_s": null
  },
  {
   "kind": "experiment",
   "id": 12,
   "ts": "2026-10-20T01:15:28Z",
   "message": "DFlash drafter (block 8) replacing MTP + size KV/mamba pools for batch 1 (max 4 reqs, 64k tokens) so the draft fits",
   "decision": "INVALID",
   "reasons": [
    "RuntimeError: server process exited before becoming ready"
   ],
   "score": null,
   "tps": null,
   "ttft_ms": null,
   "accuracy": null,
   "cost_usd": 0.2926,
   "patch": "results/patches/0012.diff",
   "startup_s": null
  },
  {
   "kind": "experiment",
   "id": 13,
   "ts": "2026-10-20T01:18:14Z",
   "message": "DFlash drafter (block 8) + batch-1 pools + explicit --page-size 256 (DSA kpool needs 4x64 physical pages)",
   "decision": "INVALID",
   "reasons": [
    "RuntimeError: server process exited before becoming ready"
   ],
   "score": null,
   "tps": null,
   "ttft_ms": null,
   "accuracy": null,
   "cost_usd": 0.2969,
   "patch": "results/patches/0013.diff",
   "startup_s": null
  }
 ]
};
