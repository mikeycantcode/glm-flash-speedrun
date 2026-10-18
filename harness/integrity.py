"""Tamper evidence: harness hashing, result signing, foreign-weight scan."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path

HARNESS_DIR = Path(__file__).parent
WEIGHT_SUFFIXES = (".safetensors", ".bin", ".pt", ".pth", ".gguf", ".ckpt", ".npz", ".onnx", ".engine")
WEIGHT_MIN_BYTES = 100 * 1024 * 1024


def tree_hash(root: Path, ignore: tuple[str, ...] = ("__pycache__", ".DS_Store")) -> str:
    """sha256 over (relative path, content) of every file under root, sorted."""
    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if any(part in ignore for part in path.relative_to(root).parts):
            continue
        h.update(rel.encode() + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return h.hexdigest()


def harness_hash() -> str:
    return tree_hash(HARNESS_DIR)


def canonical(record: dict) -> bytes:
    return json.dumps(record, sort_keys=True, separators=(",", ":")).encode()


def sign(record: dict, key: bytes) -> str:
    return hmac.new(key, canonical(record), hashlib.sha256).hexdigest()


def verify(record: dict, signature: str, key: bytes) -> bool:
    return hmac.compare_digest(sign(record, key), signature)


def scan_foreign_weights(roots: list[str], allowed_prefixes: list[str]) -> list[str]:
    """Large weight-like files outside the allowed (read-only, pinned) model dirs.

    Blocks baking a different model into the image and serving it instead.
    """
    found = []
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            if any(dirpath.startswith(p) for p in allowed_prefixes) or dirpath.startswith(("/proc", "/sys", "/dev")):
                dirnames.clear()
                continue
            for name in filenames:
                if not name.endswith(WEIGHT_SUFFIXES):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    if os.path.getsize(path) >= WEIGHT_MIN_BYTES and not os.path.islink(path):
                        found.append(path)
                except OSError:
                    pass
    return found
