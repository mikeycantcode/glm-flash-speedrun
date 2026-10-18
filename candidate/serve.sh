#!/usr/bin/env bash
# Candidate server launch. EDITABLE.
# Contract: serve an OpenAI-compatible /v1/models + streaming /v1/completions on
# 127.0.0.1:$PORT for the checkpoint in $MODEL_DIR. Runs as an unprivileged user
# with no network. Writable: $HOME, /tmp, $CACHE_DIR (persists across runs).
set -euo pipefail

exec python3 -m sglang.launch_server \
  --model-path "$MODEL_DIR" \
  --served-model-name glm \
  --quantization modelopt_fp4 \
  --tp-size 1 \
  --dsa-prefill-backend trtllm \
  --dsa-decode-backend trtllm \
  --kv-cache-dtype fp8_e4m3 \
  --moe-runner-backend flashinfer_cutlass \
  --mem-fraction-static 0.85 \
  --host 127.0.0.1 \
  --port "$PORT"
