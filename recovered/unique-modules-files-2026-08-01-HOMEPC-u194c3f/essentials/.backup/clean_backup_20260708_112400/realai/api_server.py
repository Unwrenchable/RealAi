"""RealAI API Server - Unified Fusion-Authoritative HTTP Server

This server keeps Fusion UI + static assets as the authoritative root experience
while exposing unified API endpoints inspired by the structured router.

Design goals:
- Fusion UI priority on `/`, `/ui`, `/index.html`
- Static assets served from `fusion-ui/`
- Hardened JSON validation for `/v1/chat/completions` (400 on invalid payload)
- Deterministic stub fallback for clean branch operation
- Minimal unified endpoints:
  - GET  /health
  - GET  /v1/models
  - GET  /v1/providers
  - POST /v1/chat/completions
  - POST /v1/embeddings
  - POST /v1/tasks
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

from realai.server.router import (
    RequestValidationError,
    handle_embeddings_request,
    handle_models_list,
    handle_providers_list,
    _require_dict,
    _require_messages,
)

DB_PATH = os.environ.get("REALAI_DB_PATH", "realai.db")
CLEAN_STUB_FLAG = os.environ.get("REALAI_CLEAN_STUB", "true").lower() in ("1", "true", "yes", "on")


def init_db():
    """Initialize minimal local DB used for request audit history."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at INTEGER,
            method TEXT,
            path TEXT,
            model TEXT,
            prompt TEXT,
            status_code INTEGER
        )
        """
    )
    conn.commit()
    conn.close()


def _read_json_or_error(handler: "RealAIAPIHandler"):
    """Return (payload, error_msg). payload is dict/list/None."""
    content_length = int(handler.headers.get("Content-Length", "0") or "0")
    raw = handler.rfile.read(content_length) if content_length > 0 else b""
    if not raw:
        return {}, None
    try:
        payload = json.loads(raw.decode("utf-8"))
        return payload, None
    except Exception:
        return None, "Request body must be valid JSON."


def _json_response(handler: "RealAIAPIHandler", status_code: int, payload):
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(json.dumps(payload).encode("utf-8"))


def _html_response(handler: "RealAIAPIHandler", status_code: int, html: str):
    handler.send_response(status_code)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.end_headers()
    handler.wfile.write(html.encode("utf-8"))


class RealAIAPIHandler(BaseHTTPRequestHandler):
    def _log_request_row(self, method: str, path: str, model: str, prompt: str, status_code: int):
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO requests (created_at, method, path, model, prompt, status_code)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (int(time.time()), method, path, model, prompt, status_code),
            )
            conn.commit()
            conn.close()
        except Exception as exc:
            print(f"Warning: failed to write request audit row: {exc}")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        fusion_dir = os.environ.get("REALAI_UI_PATH", "fusion-ui")
        wants_fusion = os.environ.get("REALAI_DEFAULT_UI", "fusion") == "fusion"
        fusion_root = Path(__file__).resolve().parent.parent / fusion_dir
        index_path = fusion_root / "index.html"

        # Fusion UI priority
        if path in ("/", "/ui", "/index.html"):
            print(
                f"DEBUG Fusion: wants_fusion={wants_fusion}, "
                f"path={fusion_dir}, exists={index_path.exists()}"
            )
            if wants_fusion and index_path.exists():
                html = index_path.read_text(encoding="utf-8")
                print(f"✅ Serving Fusion UI from {fusion_dir}/index.html")
                _html_response(self, 200, html)
                return
            _html_response(
                self,
                200,
                "<h1>RealAI Fusion UI</h1><p>Fusion UI not found. Check REALAI_UI_PATH.</p>",
            )
            return

        if path == "/health":
            _json_response(self, 200, {"status": "ok"})
            return

        if path == "/v1/models":
            try:
                _json_response(self, 200, handle_models_list())
            except Exception as exc:
                _json_response(self, 500, {"error": {"message": f"models error: {exc}"}})
            return

        if path == "/v1/providers":
            try:
                _json_response(self, 200, handle_providers_list())
            except Exception as exc:
                _json_response(self, 500, {"error": {"message": f"providers error: {exc}"}})
            return

        # Static assets from fusion-ui/
        if path and path != "/":
            rel = path.lstrip("/")
            if ".." not in rel:
                fpath = fusion_root / rel
                if fpath.exists() and fpath.is_file():
                    data = fpath.read_bytes()
                    suffix = fpath.suffix.lower()
                    self.send_response(200)
                    if suffix == ".js":
                        self.send_header("Content-Type", "text/javascript; charset=utf-8")
                    elif suffix == ".css":
                        self.send_header("Content-Type", "text/css; charset=utf-8")
                    elif suffix in (".html", ".htm"):
                        self.send_header("Content-Type", "text/html; charset=utf-8")
                    else:
                        self.send_header("Content-Type", "application/octet-stream")
                    self.end_headers()
                    self.wfile.write(data)
                    print(f"✅ Served static asset: {rel}")
                    return

        _json_response(self, 404, {"error": {"message": "Not found"}})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        payload, parse_error = _read_json_or_error(self)
        if parse_error:
            _json_response(self, 400, {"error": {"message": parse_error}})
            return

        # Hardened chat endpoint
        if path == "/v1/chat/completions":
            try:
                body = _require_dict(payload)
                messages = _require_messages(body.get("messages"))
                model = body.get("model", "realai-2.0")
                prompt = ""
                for msg in messages:
                    if msg.get("role") == "user":
                        prompt = msg.get("content", "") or prompt

                if CLEAN_STUB_FLAG:
                    response = {
                        "id": "chatcmpl-realai-stub",
                        "object": "chat.completion",
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "message": {
                                    "role": "assistant",
                                    "content": "Hello from RealAI stub",
                                },
                                "finish_reason": "stop",
                            }
                        ],
                    }
                else:
                    response = {
                        "id": "chatcmpl-realai-minimal",
                        "object": "chat.completion",
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "message": {
                                    "role": "assistant",
                                    "content": "RealAI response pipeline is not configured.",
                                },
                                "finish_reason": "stop",
                            }
                        ],
                    }

                self._log_request_row("POST", path, model, prompt, 200)
                _json_response(self, 200, response)
                return
            except RequestValidationError as exc:
                _json_response(self, 400, {"error": {"message": str(exc)}})
                return
            except Exception:
                _json_response(self, 500, {"error": {"message": "Internal server error"}})
                return

        if path == "/v1/embeddings":
            try:
                response = handle_embeddings_request(payload or {})
                _json_response(self, 200, response)
                return
            except RequestValidationError as exc:
                _json_response(self, 400, {"error": {"message": str(exc)}})
                return
            except Exception as exc:
                _json_response(self, 500, {"error": {"message": f"embeddings error: {exc}"}})
                return

        if path == "/v1/tasks":
            body = payload if isinstance(payload, dict) else {}
            task_name = body.get("task")
            if not isinstance(task_name, str) or not task_name.strip():
                _json_response(self, 400, {"error": {"message": "task is required."}})
                return
            result = {
                "id": f"task-{int(time.time())}",
                "task": task_name,
                "status": "queued",
                "context": body.get("context", ""),
            }
            _json_response(self, 200, result)
            return

        _json_response(self, 404, {"error": {"message": "Not found"}})

    def do_DELETE(self):
        _json_response(self, 404, {"error": {"message": "Not found"}})

    def log_message(self, fmt, *args):
        print(f"[{self.log_date_time_string()}] {fmt % args}")


def run_server(host: str = "127.0.0.1", port: int = 8000):
    init_db()
    httpd = HTTPServer((host, port), RealAIAPIHandler)
    print(f"Server running at http://{host}:{port}")
    print(f"→ Fusion UI: http://{host}:{port}/")
    print("→ Unified endpoints: /health, /v1/models, /v1/providers, /v1/chat/completions, /v1/embeddings, /v1/tasks")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down...")


if __name__ == "__main__":
    run_server()
