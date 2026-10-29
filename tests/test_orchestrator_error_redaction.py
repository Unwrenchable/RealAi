"""Callers get a generic error + id; details stay in the server log only."""
import json
import logging
import re
from pathlib import Path

import pytest

from realai.orchestration import v3_orchestrator as O

FAKE = "FAKE-secret-C:/Users/nobody/private/path-0000"
SRC = (Path(__file__).resolve().parents[1] / "realai" / "orchestration" / "v3_orchestrator.py").read_text(encoding="utf-8")


def _boom(*a, **k):
    raise RuntimeError(FAKE)


def _ids(caplog):
    return re.findall(r"internal_error id=([0-9a-f]{12})", caplog.text)


def _check(out, caplog):
    blob = json.dumps(out)
    assert "trace" not in out and "Traceback" not in blob and FAKE not in blob
    assert out["error"] == "internal_error" and out["ok"] is False
    assert re.fullmatch(r"[0-9a-f]{12}", out["error_id"])
    assert out["error_id"] in _ids(caplog)
    assert FAKE in caplog.text  # full detail is kept server-side


def test_helper(caplog):
    caplog.set_level(logging.ERROR, logger="realai.v3_orchestrator")
    try:
        _boom()
    except RuntimeError as e:
        out = O._internal_error("unit", e, craft_action="x")
    _check(out, caplog)
    assert out["craft_action"] == "x" and "error_type" not in out


def test_debug_flag_adds_only_type(caplog, monkeypatch):
    monkeypatch.setenv("REALAI_DEBUG_ERRORS", "1")
    caplog.set_level(logging.ERROR, logger="realai.v3_orchestrator")
    out = O._internal_error("unit", RuntimeError(FAKE))
    _check(out, caplog)
    assert out["error_type"] == "RuntimeError"


def test_run_tool_redacts(caplog, monkeypatch):
    caplog.set_level(logging.ERROR, logger="realai.v3_orchestrator")
    import realai.v3_runtime_bridge as B

    monkeypatch.setattr(B, "execute_registry_tool", _boom)
    out = O._run_tool("ability.definitely_not_special_xyz", {})
    _check(out, caplog)


def test_hive_status_redacts(caplog, monkeypatch):
    caplog.set_level(logging.ERROR, logger="realai.v3_orchestrator")
    import realai.v3_runtime_bridge as B

    monkeypatch.setattr(B, "hive_agents_status", _boom)
    out = O._hive_status({})
    _check(out["agents"], caplog)


def test_no_trace_left_in_source():
    assert "traceback.format_exc()" not in SRC
    assert '"trace":' not in SRC


@pytest.mark.parametrize("route", ["/v1/deepen", "/v1/weights/scan"])
def test_routes_use_helper(route):
    i = SRC.index(f'if path == "{route}":')
    block = SRC[i : i + 2500]
    assert f'_internal_error("route:{route}", e)' in block


# --- follow-up (#200 Low + remaining str(e) sites) ---------------------------


def test_extra_cannot_override_fixed_keys(caplog):
    caplog.set_level(logging.ERROR, logger="realai.v3_orchestrator")
    out = O._internal_error("unit", RuntimeError(FAKE), ok=True, error=FAKE, error_id="attacker")
    _check(out, caplog)
    assert out["ok"] is False and out["error"] == "internal_error" and out["error_id"] != "attacker"


def test_ref_helper(caplog):
    caplog.set_level(logging.ERROR, logger="realai.v3_orchestrator")
    ref = O._internal_error_ref("unit", RuntimeError(FAKE))
    assert re.fullmatch(r"internal_error:[0-9a-f]{12}", ref)
    assert ref.split(":")[1] in _ids(caplog) and FAKE in caplog.text


def test_no_bare_exception_text_in_source():
    # every former str(e)/str(exc)/str(e2) caller-facing site now goes through the helper
    assert not re.search(r"str\((e|e2|exc)\)", SRC)
    assert '"fallback_error"' not in SRC


@pytest.fixture
def server():
    import threading
    from http.server import ThreadingHTTPServer

    srv = ThreadingHTTPServer(("127.0.0.1", 0), O.Handler)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    yield srv.server_address[1]
    srv.shutdown()
    srv.server_close()


def _req(port, method, path, body=None):
    import urllib.error
    import urllib.request

    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", data=data, method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def test_route_500_does_not_leak(server, caplog, monkeypatch):
    caplog.set_level(logging.ERROR, logger="realai.v3_orchestrator")
    import realai.agent_activity as A

    monkeypatch.setattr(A, "load_profiles", _boom)
    code, text = _req(server, "GET", "/v1/agents/profiles")
    assert code == 500 and FAKE not in text
    out = json.loads(text)
    _check(out, caplog)


def test_health_vulkan_body_does_not_leak(server, caplog, monkeypatch):
    caplog.set_level(logging.ERROR, logger="realai.v3_orchestrator")
    monkeypatch.setattr(O, "_proxy", _boom)
    code, text = _req(server, "GET", "/health")
    assert FAKE not in text
    assert "internal_error:" in text


def test_tools_execute_internal_error_is_500(server, caplog, monkeypatch):
    caplog.set_level(logging.ERROR, logger="realai.v3_orchestrator")
    for k in ("REALAI_TOOLS_AUTH", "REALAI_ENV"):
        monkeypatch.delenv(k, raising=False)
    import realai.v3_runtime_bridge as B

    monkeypatch.setattr(B, "execute_registry_tool", _boom)
    code, text = _req(server, "POST", "/v1/tools/execute", {"name": "ability.definitely_not_special_xyz"})
    assert code == 500 and FAKE not in text
    _check(json.loads(text)["result"], caplog)
