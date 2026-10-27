"""Unified WSGI entrypoint (ported from RealAi-unified ``realai/unified_server.py``).

Thin WSGI wrapper over live's ``realai.server.router.dispatch_request`` so the
structured router can be served with stdlib ``wsgiref`` (no FastAPI needed).
Live's FastAPI app (``realai.server.app``) remains the primary server.
"""
from __future__ import annotations

import json
from http import HTTPStatus

from .server.router import dispatch_request

JSON = "application/json"


def _status_message(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "OK"


def _respond(start_response, code: int, data, content_type: str = JSON):
    body = json.dumps(data).encode("utf-8")
    start_response(f"{code} {_status_message(code)}", [("Content-Type", content_type), ("Content-Length", str(len(body)))])
    return [body]


def _root_info():
    info = {
        "service": "RealAI",
        "message": "Unified API and runtime entrypoint is running.",
        "endpoints": ["/health", "/v1/models", "/v1/chat/completions", "/v1/capabilities", "/v1/providers"],
    }
    try:
        from .model_registry import MODEL_REGISTRY

        info["capabilities"] = MODEL_REGISTRY.list_capabilities()
    except Exception:  # registry is optional for the root banner
        info["capabilities"] = []
    return info


def create_unified_app():
    """Create a WSGI app serving /, /health, /v1/capabilities and every router route."""

    def app(environ, start_response):
        path = environ.get("PATH_INFO", "/") or "/"
        method = environ.get("REQUEST_METHOD", "GET").upper()

        if method == "GET" and path == "/":
            return _respond(start_response, 200, _root_info())
        if method == "GET" and path == "/v1/capabilities":
            from .model_registry import MODEL_REGISTRY

            return _respond(start_response, 200, MODEL_REGISTRY.to_capabilities_payload())
        if method not in {"GET", "POST"}:
            return _respond(start_response, 405, {"error": {"message": "Method not allowed"}})

        payload = None
        try:
            size = int(environ.get("CONTENT_LENGTH") or 0)
        except ValueError:
            size = 0
        if size > 0:
            raw = environ["wsgi.input"].read(size)
            if raw:
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except ValueError:
                    return _respond(start_response, 400, {"error": {"message": "Request body must be valid JSON."}})

        status_code, data, content_type = dispatch_request(method, path, payload)
        return _respond(start_response, status_code, data, content_type)

    return app


def run_server(host: str = "127.0.0.1", port: int = 8000):
    from wsgiref.simple_server import make_server

    httpd = make_server(host, int(port), create_unified_app())
    print(f"RealAI unified server listening on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    run_server()
