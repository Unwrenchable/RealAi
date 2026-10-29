"""tool_router_plugins LIVE gate: real HTTP integration for POST /v1/tools/route (default on, routes only).

Serves the structured server's WSGI app (realai.server.app.wsgi_app) on 127.0.0.1:0 and, when FastAPI and
httpx are installed, the FastAPI app too. Proves: on by default, opt-out works, nothing is executed or audited,
bad/oversized input is refused, and /v1/providers/route stays opt-in.
"""
import json
import threading
import urllib.error
import urllib.request
from wsgiref.simple_server import WSGIRequestHandler, make_server

import pytest

ENV = ("REALAI_ROUTING_ROUTES", "REALAI_UNIFIED_ROUTES", "REALAI_SERVER_MERGED_ROUTES", "REALAI_TOOLS_ROUTE")


class _Quiet(WSGIRequestHandler):
    def log_message(self, *a):
        pass


@pytest.fixture
def clean_env(monkeypatch):
    for k in ENV:
        monkeypatch.delenv(k, raising=False)
    return monkeypatch


@pytest.fixture(scope="module")
def server():
    import importlib

    wsgi_app = importlib.import_module("realai.server.app").wsgi_app

    srv = make_server("127.0.0.1", 0, wsgi_app, handler_class=_Quiet)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1]
    srv.shutdown()
    srv.server_close()


def post(port, path, body):
    data = body if isinstance(body, bytes) else json.dumps(body).encode()
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8") or "{}")


def test_on_by_default_routes_without_executing(server, clean_env):
    from realai.server import tools_runtime

    before = list(tools_runtime.TOOLS.list_audit())
    code, body = post(server, "/v1/tools/route", {"text": "read the file in this directory"})
    assert code == 200 and body["ok"] is True
    assert body["selected"] == "file_read" and body["provider"] == "local"
    assert body["routing"]["executes"] is False
    assert body["candidates"] and body["candidates"][0]["tool"] == "file_read"
    code, body = post(server, "/v1/tools/route", {"text": "search the latest news", "allowed_tools": ["web_search", "file_read"]})
    assert code == 200 and body["selected"] == "web_search"
    assert list(tools_runtime.TOOLS.list_audit()) == before  # nothing executed / audited


def test_opt_out(server, clean_env):
    clean_env.setenv("REALAI_TOOLS_ROUTE", "0")
    assert post(server, "/v1/tools/route", {"text": "search the web"})[0] == 404


def test_bad_input_refused(server, clean_env):
    assert post(server, "/v1/tools/route", {})[0] == 400
    assert post(server, "/v1/tools/route", {"text": "x" * 20_001})[0] == 400
    assert post(server, "/v1/tools/route", {"text": "search", "allowed_tools": ["t%d" % i for i in range(501)]})[0] == 400
    assert post(server, "/v1/tools/route", b"{not json")[0] == 400


def test_providers_route_still_opt_in(server, clean_env):
    assert post(server, "/v1/providers/route", {})[0] == 404


def test_plugin_reports_live():
    from realai.plugins.tool_router import register
    from realai.ability_catalog import RUNDOWN_ABILITIES

    assert register(None)["status"] == "LIVE"
    assert [e["status"] for e in RUNDOWN_ABILITIES if e["id"] == "tool_router_plugins"] == ["LIVE"]


def test_fastapi_app_serves_route(clean_env):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    import importlib

    app_mod = importlib.import_module("realai.server.app")  # package attr `app` shadows the module

    if not hasattr(app_mod.app, "routes"):
        pytest.skip("FastAPI not active")
    client = TestClient(app_mod.app)
    r = client.post("/v1/tools/route", json={"text": "check my solana wallet"})
    assert r.status_code == 200 and r.json()["selected"] == "web3_solana_rpc" and r.json()["routing"]["executes"] is False
    clean_env.setenv("REALAI_TOOLS_ROUTE", "0")
    assert client.post("/v1/tools/route", json={"text": "search"}).status_code == 404