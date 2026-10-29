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
