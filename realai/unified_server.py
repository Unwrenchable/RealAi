"""Unified RealAI entrypoint that combines the legacy and structured server paths."""

import json
import os
from typing import Callable, Dict, Tuple

from .model_registry import MODEL_REGISTRY
from .server.app import app as structured_app
from .server.router import dispatch_request


def create_unified_app():
    """Create a WSGI-compatible app that serves health and API routes."""

    def app(environ, start_response):
        path = environ.get("PATH_INFO", "/")
        method = environ.get("REQUEST_METHOD", "GET")

        if method == "GET" and path == "/health":
            body = json.dumps({
                "status": "ok",
                "service": "realai",
                "mode": "unified",
                "version": "v1-v3-compatible",
            }).encode("utf-8")
            headers = [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(body))),
            ]
            start_response("200 OK", headers)
            return [body]

        if method == "GET" and path == "/":
            body = json.dumps({
                "service": "RealAI",
                "message": "Unified API and runtime entrypoint is running.",
                "endpoints": ["/health", "/v1/models", "/v1/chat/completions", "/v1/capabilities", "/v1/providers"],
                "capabilities": MODEL_REGISTRY.list_capabilities(),
            }).encode("utf-8")
            headers = [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(body))),
            ]
            start_response("200 OK", headers)
            return [body]

        if method == "GET" and path == "/v1/capabilities":
            body = json.dumps(MODEL_REGISTRY.to_capabilities_payload()).encode("utf-8")
            headers = [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(body))),
            ]
            start_response("200 OK", headers)
            return [body]

        if method == "GET" and path == "/v1/providers":
            from .server.providers import list_providers

            body = json.dumps({"object": "list", "data": list_providers()}).encode("utf-8")
            headers = [
                ("Content-Type", "application/json"),
                ("Content-Length", str(len(body))),
            ]
            start_response("200 OK", headers)
            return [body]

        if method in {"GET", "POST"}:
            content_length = environ.get("CONTENT_LENGTH") or "0"
            try:
                body_size = int(content_length)
            except ValueError:
                body_size = 0

            payload = None
            if body_size > 0:
                raw_body = environ.get("wsgi.input", b"").read(body_size)
                if raw_body:
                    try:
                        payload = json.loads(raw_body.decode("utf-8"))
                    except ValueError:
                        body = json.dumps({"error": {"message": "Request body must be valid JSON."}}).encode("utf-8")
                        headers = [
                            ("Content-Type", "application/json"),
                            ("Content-Length", str(len(body))),
                        ]
                        start_response("400 Bad Request", headers)
                        return [body]

            status_code, data, content_type = dispatch_request(method, path, payload)
            body = json.dumps(data).encode("utf-8")
            headers = [
                ("Content-Type", content_type),
                ("Content-Length", str(len(body))),
            ]
            start_response(f"{status_code} { _status_message(status_code) }", headers)
            return [body]

        body = json.dumps({"error": {"message": "Method not allowed"}}).encode("utf-8")
        headers = [
            ("Content-Type", "application/json"),
            ("Content-Length", str(len(body))),
        ]
        start_response("405 Method Not Allowed", headers)
        return [body]

    return app


def _status_message(status_code: int) -> str:
    return {
        200: "OK",
        400: "Bad Request",
        404: "Not Found",
        405: "Method Not Allowed",
        500: "Internal Server Error",
    }.get(status_code, "OK")


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the unified server using the structured router."""
    from wsgiref.simple_server import make_server

    app = create_unified_app()
    httpd = make_server(host, int(port), app)
    print(f"RealAI unified server listening on http://{host}:{port}")
    httpd.serve_forever()


app = create_unified_app()
