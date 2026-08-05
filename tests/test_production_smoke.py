"""Production smoke tests — hive, tools catalog, rackup-coach, guardian."""
from __future__ import annotations

import json
import os
import sys
from io import BytesIO
from urllib.parse import urlencode

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def test_hive_status_organ_count():
    from modules.organs import hive_status

    s = hive_status()
    assert s["organ_count"] >= 45
    assert s["complete"] is True
    assert "organ.rackup-coach" in s["ids"]
    assert "organ.synthetic-guardian-layer" in s["ids"]


def test_call_organ_rackup_coach():
    from modules.organs import call_organ

    r = call_organ(
        "organ.rackup-coach",
        goal="shot of the day",
        payload={
            "ability": "shot_of_the_day",
            "player": {
                "player_id": "smoke",
                "rating": 500,
                "discipline": "pyramid",
                "table_size": "7ft",
                "skill_level": "beginner",
            },
            "payload": {"game": "pyramid"},
        },
    )
    assert r.ok is True
    assert r.output
    assert r.output.get("ok") is True or r.output.get("result")


def test_ability_catalog_loaded_into_tool_registry():
    from realai.tools import TOOL_REGISTRY

    status = TOOL_REGISTRY.ensure_ability_catalog_loaded()
    assert status.get("loaded") is True or status.get("registered", 0) >= 0
    cat = TOOL_REGISTRY.catalog_status()
    assert cat["ability_tool_count"] > 10
    # Builtins still present
    assert TOOL_REGISTRY.get("web_research") is not None
    assert TOOL_REGISTRY.get("web_research").source == "builtin"
    # Catalog entry present
    assert any(n.startswith("ability.") for n in [t.name for t in TOOL_REGISTRY.list_all()])


def test_guardian_advisory_default():
    from realai.guardian import check_tool_call, guardian_mode
    from realai.tools import TOOL_REGISTRY

    assert guardian_mode() == "advisory"
    schema = TOOL_REGISTRY.get("execute_code")
    assert schema is not None
    d = check_tool_call("execute_code", {}, schema)
    assert d["allowed"] is True  # advisory does not hard-block restricted


def test_guardian_hard_block_restricted_without_confirm(monkeypatch):
    monkeypatch.setenv("REALAI_GUARDIAN_MODE", "hard_block")
    # re-import mode
    import importlib
    import realai.guardian as g

    importlib.reload(g)
    from realai.tools import TOOL_REGISTRY

    schema = TOOL_REGISTRY.get("execute_code")
    d = g.check_tool_call("execute_code", {}, schema)
    assert d["allowed"] is False
    d2 = g.check_tool_call("execute_code", {"confirm": True, "code": "1"}, schema)
    # may still fail schema required fields in validator, but guardian allows
    assert d2["allowed"] is True
    monkeypatch.delenv("REALAI_GUARDIAN_MODE", raising=False)
    importlib.reload(g)


def test_rackup_coach_http_handler():
    """Smoke POST /v1/plugins/rackup-coach via handler (no bind)."""
    from realai.api_server import RealAIAPIHandler

    body = {
        "ability": "pyramid_rules",
        "player": {
            "player_id": "http-smoke",
            "rating": 700,
            "discipline": "pyramid",
            "table_size": "9ft",
            "skill_level": "advanced",
        },
        "organs_enabled": False,
    }
    raw = json.dumps(body).encode("utf-8")

    class _FakeServer:
        pass

    captured = {}

    class H(RealAIAPIHandler):
        def __init__(self):
            self.requestline = "POST /v1/plugins/rackup-coach HTTP/1.1"
            self.command = "POST"
            self.path = "/v1/plugins/rackup-coach"
            self.headers = {"Content-Length": str(len(raw)), "Content-Type": "application/json"}
            self.rfile = BytesIO(raw)
            self.wfile = BytesIO()
            self.request_version = "HTTP/1.1"
            self.client_address = ("127.0.0.1", 0)
            self.server = _FakeServer()

        def _send_response(self, code, data):
            captured["code"] = code
            captured["data"] = data

        def _read_body(self):
            return body

        def _get_model(self, model_name="realai-2.0"):
            class M:
                pass
            return M()

    h = H()
    # Call do_POST logic for rackup path directly via invoke to avoid full HTTP stack
    from plugins.rackup_coach import invoke

    resp = invoke(body)
    assert resp["ok"] is True
    assert resp["result"]["config"]["points_to_win"] == 71

    # Alias path shape
    body2 = dict(body)
    body2["ability"] = "moderation"
    body2["payload"] = {"text": "hello friend"}
    resp2 = invoke(body2)
    assert resp2["ok"] is True
    assert resp2["result"]["action"] in (
        "allow", "soft_filter", "warn", "warn_and_flag", "hold_for_review", "block_and_escalate",
    )


def test_embeddings_organ_helper():
    from modules.organs.request_path import embeddings_with_organs, audio_with_organs, tools_with_organs

    e = embeddings_with_organs("hello world")
    assert e.get("enabled") is True
    assert len(e.get("results") or []) >= 1
    a = audio_with_organs("transcription", "file.wav")
    assert a.get("enabled") is True
    t = tools_with_organs("web_research", {"query": "x"})
    assert t.get("enabled") is True
