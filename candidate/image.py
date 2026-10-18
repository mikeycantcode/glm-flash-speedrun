"""Candidate container image. EDITABLE: engine choice, version, patches, prebuilt kernels.

Runtime has no network (block_network=True): anything the server needs at
runtime must be baked in here or come from the pinned model volume.
"""

import modal

SGLANG_IMAGE = "lmsysorg/sglang:v0.5.22-cu130"


def build_image() -> modal.Image:
    return (
        modal.Image.from_registry(SGLANG_IMAGE)
        .entrypoint([])
        .run_commands("python3 -m pip install --no-cache-dir 'transformers==5.20.1'")
    )
