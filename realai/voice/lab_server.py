"""RealAI Voice Lab HTTP server (local).

Default: http://127.0.0.1:8890  (does not collide with Vulkan :8080 or Hive :8001)

  GET  /health
  GET  /v1/voice/inventory
  GET  /v1/voice/health
  POST /v1/audio/speech   {"input"|"text", "voice"?, "backend"?} → WAV or JSON+b64
  POST /v1/audio/transcriptions  {"audio_b64"} → {"text"}
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse


HOST = os.environ.get("REALAI_VOICE_LAB_HOST") or "127.0.0.1"
PORT = int(os.environ.get("REALAI_VOICE_LAB_PORT") or "8890")


def _json_bytes(payload: Dict[str, Any], status: int = 200) -> tuple[int, bytes, str]:
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return status, raw, "application/json; charset=utf-8"


class VoiceLabHandler(BaseHTTPRequestHandler):
    server_version = "RealAIVoiceLab/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[voice-lab] " + (fmt % args) + "\n")

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _cors(self) -> None:
        origin = (self.headers.get("Origin") or "").strip()
        if origin in ("http://127.0.0.1:8001", "http://localhost:8001"):
            self.send_header("Access-Control-Allow-Origin", origin)
        else:
            self.send_header("Access-Control-Allow-Origin", "http://127.0.0.1:8001")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization, x-realai-voice, X-RealAI-Voice, X-Request-Id, X-Provider, X-Base-URL, X-RealAI-Tools",
        )
        self.send_header("Access-Control-Max-Age", "86400")

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path.rstrip("/") or "/"
        from realai.voice.provider import get_voice_provider

        provider = get_voice_provider()
        if path in ("/", "/health", "/v1/voice/health"):
            status, body, ctype = _json_bytes(provider.health())
            self._send(status, body, ctype)
            return
        if path == "/v1/voice/inventory":
            status, body, ctype = _json_bytes(provider.inventory())
            self._send(status, body, ctype)
            return
        status, body, ctype = _json_bytes({"ok": False, "error": "not_found", "path": path}, 404)
        self._send(status, body, ctype)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        qs = parse_qs(parsed.query)
        body = self._read_json()
        from realai.voice.provider import get_voice_provider

        provider = get_voice_provider()

        if path == "/v1/audio/speech":
            text = str(body.get("input") or body.get("text") or "").strip()
            voice = body.get("voice") or body.get("voice_id")
            backend = body.get("backend") or body.get("model")
            want_json = (
                str(body.get("response_format") or "").lower() == "json"
                or "application/json" in (self.headers.get("Accept") or "")
                or qs.get("format", [""])[0] == "json"
            )
            result = provider.speak(
                text,
                voice=str(voice) if voice else None,
                backend=str(backend) if backend else None,
                prepare=True,
                as_base64=want_json,
            )
            if want_json:
                # Drop raw bytes if present
                result.pop("audio", None)
                status, raw, ctype = _json_bytes(result, 200 if result.get("ok") else 502)
                self._send(status, raw, ctype)
                return
            audio = result.pop("audio", None)
            if not result.get("ok") or not audio:
                status, raw, ctype = _json_bytes(
                    {k: v for k, v in result.items() if k != "audio"},
                    502,
                )
                self._send(status, raw, ctype)
                return
            self._send(200, audio, "audio/wav")
            return

        if path == "/v1/audio/transcriptions":
            b64 = str(body.get("audio_b64") or body.get("file") or "")
            try:
                audio = base64.b64decode(b64) if b64 else b""
            except Exception:
                audio = b""
            result = provider.listen(audio)
            status, raw, ctype = _json_bytes(result, 200 if result.get("ok") else 502)
            self._send(status, raw, ctype)
            return

        if path == "/v1/voice/hive-speak":
            text = str(body.get("text") or body.get("input") or "").strip()
            intent = str(body.get("intent") or "chat")
            result = provider.hive_speak(text, intent=intent)
            status, raw, ctype = _json_bytes(result, 200 if result.get("ok") else 502)
            self._send(status, raw, ctype)
            return

        status, raw, ctype = _json_bytes({"ok": False, "error": "not_found", "path": path}, 404)
        self._send(status, raw, ctype)


def serve(host: str = HOST, port: int = PORT) -> None:
    httpd = ThreadingHTTPServer((host, port), VoiceLabHandler)
    print(f"RealAI Voice Lab on http://{host}:{port}", flush=True)
    print("  GET  /health  /v1/voice/inventory", flush=True)
    print("  POST /v1/audio/speech  /v1/audio/transcriptions  /v1/voice/hive-speak", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nvoice lab stopped", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RealAI Voice Lab server")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args(argv)
    serve(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
