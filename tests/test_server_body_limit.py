"""Security LOW: request bodies above MAX_BODY_BYTES (~1 MB) get 413 on WSGI, FastAPI and the ASGI fallback."""
import asyncio
import io
import json

import pytest

import importlib

app_mod = importlib.import_module("realai.server.app")


def _wsgi(body, content_length=None):
    out = {}

    def start_response(status, headers):
        out["status"] = status

    env = {
        "REQUEST_METHOD": "POST",
        "PATH_INFO": "/v1/tasks",
        "CONTENT_LENGTH": str(len(body) if content_length is None else content_length),
        "wsgi.input": io.BytesIO(body),
    }
    resp = b"".join(app_mod.wsgi_app(env, start_response))
    return out["status"], resp


def test_wsgi_rejects_oversized_body():
    status, resp = _wsgi(b"x" * (app_mod.MAX_BODY_BYTES + 1))
    assert status.startswith("413")
    assert json.loads(resp)["error"]["message"] == "Request body too large."


def test_wsgi_rejects_large_declared_length_without_reading():
    status, _ = _wsgi(b"", content_length=50 * 1024 * 1024)
    assert status.startswith("413")


def test_wsgi_allows_body_at_limit():
    status, _ = _wsgi(json.dumps({"task": "hi"}).encode())
    assert not status.startswith("413")


def _asgi_call(asgi_app, chunks, headers=()):
    sent = []
    msgs = [{"type": "http.request", "body": c, "more_body": i < len(chunks) - 1} for i, c in enumerate(chunks)]

    async def receive():
        return msgs.pop(0) if msgs else {"type": "http.disconnect"}

    async def send(m):
        sent.append(m)

    scope = {"type": "http", "method": "POST", "path": "/v1/tasks", "headers": list(headers), "query_string": b""}
    asyncio.run(asgi_app(scope, receive, send))
    return next(m["status"] for m in sent if m["type"] == "http.response.start")


def test_asgi_wrapper_rejects_streamed_oversize_without_content_length():
    async def inner(scope, receive, send):  # must never be reached
        raise AssertionError("inner app called")

    half = b"x" * (app_mod.MAX_BODY_BYTES // 2 + 1)
    assert _asgi_call(app_mod._BodyLimitASGI(inner), [half, half]) == 413


def test_asgi_wrapper_rejects_large_content_length_header():
    async def inner(scope, receive, send):
        raise AssertionError("inner app called")

    assert _asgi_call(app_mod._BodyLimitASGI(inner), [b""], headers=[(b"content-length", b"2000000")]) == 413


def test_asgi_wrapper_passes_small_body_through():
    seen = {}

    async def inner(scope, receive, send):
        seen["body"] = (await receive())["body"]
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    assert _asgi_call(app_mod._BodyLimitASGI(inner), [b'{"a":', b"1}"]) == 200
    assert seen["body"] == b'{"a":1}'


def test_fastapi_app_returns_413():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    if app_mod.FastAPI is None:
        pytest.skip("FastAPI unavailable")
    from fastapi.testclient import TestClient

    client = TestClient(app_mod.app)
    r = client.post("/v1/tasks", content=b"x" * (app_mod.MAX_BODY_BYTES + 1), headers={"content-type": "application/json"})
    assert r.status_code == 413
    assert client.get("/health").status_code != 413
