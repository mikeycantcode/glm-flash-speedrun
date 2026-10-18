"""Frozen benchmark constants. Changing anything in harness/ changes the seal."""

MODEL_REPO = "nvidia/GLM-5.3-Flash-NVFP4"
MODEL_REVISION = "da920bb0b9f4a06727223a349e55468e38352348"
MODEL_DIR = f"/models/{MODEL_REPO}/{MODEL_REVISION}"
DERIVED_ROOT = "/models/derived"  # outputs of candidate/convert.py, keyed by script hash

GPU = "B300"
GPU_NAME_MUST_CONTAIN = "B300"
CPU_CORES = 8
MEMORY_MIB = 65536

# Modal list prices (USD per second), 2026-10-18.
GPU_USD_PER_S = 0.001972
CPU_USD_PER_CORE_S = 0.0000131
MEM_USD_PER_GIB_S = 0.00000222
USD_PER_S = GPU_USD_PER_S + CPU_CORES * CPU_USD_PER_CORE_S + (MEMORY_MIB / 1024) * MEM_USD_PER_GIB_S

SERVER_PORT = 30000
SERVER_UID = 1500
SERVER_READY_TIMEOUT_S = 1200
RUN_TIMEOUT_S = 1800

# Workload: single user, batch 1.
PROMPT_TOKENS = 2048
PROMPT_TOKENS_TOLERANCE = 8
OUTPUT_TOKENS = 512
OUTPUT_TOKENS_TOLERANCE = 0.05  # client-side re-tokenized count must be within ±5%
WARMUP_REQUESTS = 2
TIMED_REQUESTS = 8
PROBES_PER_KIND = 24  # 4 kinds -> 96 graded probes per run
PROBE_MAX_TOKENS = 48
TTFT_LOOKBACK_CHUNKS = 16  # fake-early-token guard window
REQUEST_TIMEOUT_S = 120

# Keep / revert rule.
DECODE_WEIGHT = 2 / 3  # score exponents: decode counts twice as much as TTFT
TTFT_WEIGHT = 1 / 3
GUARDRAIL = 0.05  # tok/s may not regress more than 5% vs best
TTFT_GUARDRAIL = 0.50  # TTFT may regress up to 50% vs best (anti-buffering cap)
MIN_KEEP_DELTA = 0.01  # score must beat best by max(this, 2 sigma noise)
COMPRESS_RATIO_FLOOR = 0.7  # timed outputs' median zlib ratio must be >= 0.7x baseline

BUDGET_USD = 30.0

VOLUME_MODELS = "glm-flash-speedrun-models"
VOLUME_CACHE = "glm-flash-speedrun-jit-cache"
HMAC_SECRET = "speedrun-hmac"
