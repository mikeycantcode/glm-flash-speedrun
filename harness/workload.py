"""Seeded workload generation and grading.

Every run draws a fresh seed inside the GPU container, so the server cannot
precompute or cache answers. The *distribution* is fixed, which is what makes
scores comparable across runs.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from harness import config

CORPUS_DIR = Path(__file__).parent / "corpus"

# GLM-5.3 raw chat format with an empty think block: answer without reasoning.
PROMPT_PREFIX = "[gMASK]<sop><|system|>Reasoning Effort: Low<|user|>"
PROMPT_SUFFIX = "<|assistant|><think></think>"

PROBE_KINDS = ("needle_sum", "arith", "sort", "reverse")


class Tokenizer(Protocol):
    def encode(self, text: str) -> list[int]: ...
    def decode(self, ids: list[int]) -> str: ...


@dataclass(frozen=True)
class Request:
    kind: str  # "warmup", "timed", or a probe kind
    prompt: str
    max_tokens: int
    ignore_eos: bool
    answer: str | None = None


def render(user_text: str) -> str:
    return PROMPT_PREFIX + user_text + PROMPT_SUFFIX


def load_corpus() -> list[str]:
    paragraphs = []
    for path in sorted(CORPUS_DIR.glob("*.txt")):
        for para in path.read_text().split("\n\n"):
            para = " ".join(para.split())
            if len(para) > 200:
                paragraphs.append(para)
    return paragraphs


def load_words() -> list[str]:
    text = " ".join(load_corpus()).lower()
    return sorted({w for w in re.findall(r"[a-z]+", text) if 4 <= len(w) <= 9})


def _nonce(rng: random.Random) -> str:
    return f"{rng.getrandbits(64):016x}"


def timed_request(rng: random.Random, tok: Tokenizer, paragraphs: list[str], kind: str = "timed") -> Request:
    start = rng.randrange(len(paragraphs))
    passage = "\n\n".join(paragraphs[start : start + 60])
    head = f"Session {_nonce(rng)}.\n\nPassage:\n"
    tail = (
        "\n\nContinue this story in the same style for at least 800 words. "
        "Keep writing new events; do not summarize or stop early."
    )
    passage_ids = tok.encode(passage)
    k = config.PROMPT_TOKENS - len(tok.encode(render(head + tail)))
    for _ in range(4):
        prompt = render(head + tok.decode(passage_ids[:k]) + tail)
        diff = config.PROMPT_TOKENS - len(tok.encode(prompt))
        if abs(diff) <= config.PROMPT_TOKENS_TOLERANCE // 2:
            break
        k += diff
    return Request(kind, prompt, config.OUTPUT_TOKENS, ignore_eos=True)


def probe_request(rng: random.Random, kind: str, words: list[str]) -> Request:
    session = f"Session {_nonce(rng)}.\n\n"
    if kind == "needle_sum":
        keys = rng.sample(words, 30)
        codes = {w: rng.randint(100, 999) for w in keys}
        a, b = rng.sample(keys, 2)
        lines = "\n".join(f"The code for {w} is {codes[w]}." for w in keys)
        user = f"{lines}\n\nWhat is the code for {a} plus the code for {b}? Reply with only the number."
        answer = str(codes[a] + codes[b])
    elif kind == "arith":
        a, b, c = rng.randint(12, 99), rng.randint(12, 99), rng.randint(100, 999)
        user = f"Compute {a} * {b} + {c}. Reply with only the number."
        answer = str(a * b + c)
    elif kind == "sort":
        ws = rng.sample(words, 7)
        user = f"Sort these words alphabetically: {', '.join(ws)}. Reply with only the sorted words, comma-separated."
        answer = ", ".join(sorted(ws))
    elif kind == "reverse":
        ws = rng.sample(words, 7)
        user = f"Write these words in reverse order: {', '.join(ws)}. Reply with only the words, comma-separated."
        answer = ", ".join(reversed(ws))
    else:
        raise ValueError(kind)
    return Request(kind, render(session + user), config.PROBE_MAX_TOKENS, ignore_eos=False, answer=answer)


def build_schedule(seed: int, tok: Tokenizer) -> list[Request]:
    """Warmups first, then timed requests shuffled among graded probes.

    Timed and probe requests share the same endpoint, batch size and sampling
    settings, so a server cannot run a different code path for one of them
    without inspecting prompt contents (which the rules forbid and audit).
    """
    rng = random.Random(seed)
    paragraphs = load_corpus()
    words = load_words()
    warmups = [timed_request(rng, tok, paragraphs, "warmup") for _ in range(config.WARMUP_REQUESTS)]
    body = [timed_request(rng, tok, paragraphs) for _ in range(config.TIMED_REQUESTS)]
    body += [probe_request(rng, kind, words) for kind in PROBE_KINDS for _ in range(config.PROBES_PER_KIND)]
    rng.shuffle(body)
    return warmups + body


def _first_line(text: str) -> str:
    text = text.strip()
    return text.splitlines()[0].strip() if text else ""


def grade(req: Request, output: str) -> bool:
    line = _first_line(output)
    if req.kind in ("needle_sum", "arith"):
        m = re.search(r"-?\d[\d,]*", line)
        return bool(m) and m.group(0).replace(",", "") == req.answer
    if req.kind in ("sort", "reverse"):
        got = [w.strip().strip(".").lower() for w in line.split(",")]
        return got == req.answer.split(", ")
    raise ValueError(req.kind)
