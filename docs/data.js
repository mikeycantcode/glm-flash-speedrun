window.SPEEDRUN = {
 "generated_at": "2026-10-18 23:02 UTC",
 "repo": "https://github.com/mikeycantcode/glm-flash-speedrun",
 "budget_usd": 30.0,
 "spent_usd": 11.4034,
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
  }
 ]
};
