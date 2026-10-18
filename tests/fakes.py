"""Test doubles: a reversible toy tokenizer and an OpenAI-style streaming server with cheat modes."""

from __future__ import annotations

import json
import random
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TOKEN_RE = re.compile(r"\w+|\s|[^\w\s]")


class ToyTokenizer:
    """Word/char tokenizer with decode(encode(x)) == x."""

    def __init__(self):
        self.vocab: dict[str, int] = {}
        self.inv: list[str] = []
        self.lock = threading.Lock()

    def encode(self, text: str) -> list[int]:
        ids = []
        with self.lock:
            for piece in TOKEN_RE.findall(text):
                if piece not in self.vocab:
                    self.vocab[piece] = len(self.inv)
                    self.inv.append(piece)
                ids.append(self.vocab[piece])
        return ids

    def decode(self, ids: list[int]) -> str:
        return "".join(self.inv[i] for i in ids)


WORDS = "the of and to in he was that it his her with as had for you she not but at on said by all be".split()


def solve_probe(prompt: str) -> str:
    """An honest 'model': parse the probe and answer it."""
    if m := re.search(r"code for (\w+) plus the code for (\w+)\?", prompt):
        codes = dict(re.findall(r"The code for (\w+) is (\d+)\.", prompt))
        return str(int(codes[m.group(1)]) + int(codes[m.group(2)]))
    if m := re.search(r"Compute (\d+) \* (\d+) \+ (\d+)\.", prompt):
        a, b, c = map(int, m.groups())
        return str(a * b + c)
    if m := re.search(r"Sort these words alphabetically: ([\w, ]+)\. Reply", prompt):
        return ", ".join(sorted(m.group(1).split(", ")))
    if m := re.search(r"Write these words in reverse order: ([\w, ]+)\. Reply", prompt):
        return ", ".join(reversed(m.group(1).split(", ")))
    return "?"


class FakeServer:
    """Modes: honest, fake_first, short, early_eos, filler, wrong, burst, inflate, http_error, slow."""

    def __init__(self, mode: str = "honest", prefill_s: float = 0.03, tick_s: float = 0.001):
        self.mode, self.prefill_s, self.tick_s = mode, prefill_s, tick_s
        outer = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, *a):
                pass

            def do_GET(self):
                body = json.dumps({"data": [{"id": "glm"}]}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def do_POST(self):
                req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if outer.mode == "http_error":
                    self.send_response(500)
                    self.send_header("Content-Length", "4")
                    self.end_headers()
                    self.wfile.write(b"boom")
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Transfer-Encoding", "chunked")
                self.end_headers()
                outer.stream(self, req)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def close(self):
        self.httpd.shutdown()

    @staticmethod
    def send(handler, obj):
        data = b"data: " + (obj if isinstance(obj, bytes) else json.dumps(obj).encode()) + b"\n\n"
        handler.wfile.write(f"{len(data):x}\r\n".encode() + data + b"\r\n")
        handler.wfile.flush()

    def pieces(self, req: dict) -> tuple[list[str], str]:
        n = req["max_tokens"]
        if not req["ignore_eos"]:  # graded probe
            ans = solve_probe(req["prompt"])
            if self.mode == "wrong":
                ans = "12345"
            return [p for p in re.findall(r"\w+|\s|[^\w\s]", ans)], "stop"
        rng = random.Random(req["prompt"])
        out = []
        while len(out) < n:  # alternate word / space tokens
            out.append(" " if out and out[-1] != " " else rng.choice(WORDS) + str(rng.randint(0, 999)))
        if self.mode == "short":
            return out[: int(n * 0.6)], "length"
        if self.mode == "early_eos":
            return out, "stop"
        if self.mode == "filler":
            return out[:10] + [" ", "the"] * ((n - 10) // 2), "length"
        if self.mode == "inflate":  # each chunk claims one token but carries two words
            return [p + " x" for p in out], "length"
        return out, "length"

    def stream(self, handler, req: dict):
        pieces, finish = self.pieces(req)
        tick = self.tick_s * (3 if self.mode == "slow" else 1)
        if self.mode == "fake_first":
            self.send(handler, {"choices": [{"text": pieces[0], "finish_reason": None}]})
            time.sleep(self.prefill_s)
            pieces = pieces[1:]
        elif self.mode == "burst":
            time.sleep(self.prefill_s + tick * len(pieces))
            tick = 0
        else:
            time.sleep(self.prefill_s)
        for i, p in enumerate(pieces):
            last = i == len(pieces) - 1
            self.send(handler, {"choices": [{"text": p, "finish_reason": finish if last else None}]})
            if tick:
                time.sleep(tick)
        self.send(handler, b"[DONE]")
        handler.wfile.write(b"0\r\n\r\n")
        handler.wfile.flush()
