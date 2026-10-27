"""CLI + optional separate-port HTTP front-end for the shared voice service.

  python -m realai.voice_service health
  python -m realai.voice_service speak "Hello Travis" [--voice laura] [--backend xtts] [--out C:\\tmp\\hi.wav]
  python -m realai.voice_service serve [--port 8891]      # NOT the lab's 8890/8787; never started automatically
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from realai.voice_service import DEFAULT_PORT, get_voice_client


class _H(BaseHTTPRequestHandler):
    def _send(self, code: int, obj) -> None:
        raw = json.dumps(obj, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/") in ("", "/health", "/v1/voice-service/health"):
            return self._send(200, get_voice_client().health())
        self._send(404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") != "/v1/voice-service/speak":
            return self._send(404, {"ok": False, "error": "not_found"})
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}") if n else {}
        r = get_voice_client().speak(str(body.get("text") or body.get("input") or ""), voice=body.get("voice"),
                                     backend=body.get("backend"), save=bool(body.get("save", False)))
        self._send(200 if r.get("ok") else 502, r)

    def log_message(self, *a) -> None:
        pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m realai.voice_service")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health")
    sp = sub.add_parser("speak")
    sp.add_argument("text")
    sp.add_argument("--voice")
    sp.add_argument("--backend")
    sp.add_argument("--out")
    sv = sub.add_parser("serve")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=int(os.environ.get("REALAI_VOICE_SERVICE_PORT") or DEFAULT_PORT))
    a = ap.parse_args(argv)
    c = get_voice_client()
    if a.cmd == "health":
        print(json.dumps(c.health(), indent=2, default=str))
        return 0
    if a.cmd == "speak":
        r = c.speak(a.text, voice=a.voice, backend=a.backend, out_path=a.out)
        print(json.dumps(r, indent=2, default=str))
        return 0 if r.get("ok") else 1
    if a.port in (8890, 8787, 8000, 8001, 8080):
        print(f"refusing port {a.port}: reserved for the lab / live stack")
        return 2
    ThreadingHTTPServer((a.host, a.port), _H).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
