window.SPEEDRUN = {
 "generated_at": "2026-10-18 20:55 UTC",
 "repo": "https://github.com/mikeycantcode/glm-flash-speedrun",
 "budget_usd": 30.0,
 "spent_usd": 7.0898,
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
   "score": 92.60421202022057,
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
   "score": 99.9092524046179,
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
   "score": 100.22007647079081,
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
   "score": 99.87130316865182,
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
   "score": 125.52269571150556,
   "tps": 220.30773378352035,
   "ttft_ms": 161.8799175000163,
   "accuracy": 0.8958333333333334,
   "cost_usd": 1.5578,
   "patch": "results/patches/0001.diff",
   "startup_s": 570.28
  }
 ]
};
