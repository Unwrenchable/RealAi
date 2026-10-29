"""Tests for realai/orchestration/tool_auth.py and its wiring into /v1/tools/execute.

All tokens here are obviously fake.
"""
import logging

import pytest

from realai.orchestration import tool_auth

FAKE = "FAKE-test-token-not-a-secret-0000"
ALLOWED = "list_agents"


@pytest.fixture(autouse=True)
def _reset():
    tool_auth._limiter = None
    yield
    tool_auth._limiter = None


def env(**kw):
    base = {"REALAI_TOOLS_AUTH": "1", "REALAI_TOOLS_TOKEN": FAKE}
    base.update(kw)
    return {k: v for k, v in base.items() if v is not None}


def hdr(tok=FAKE):
    return {"Authorization": "Bearer " + tok} if tok else {}


def test_flag_off_unchanged():
    assert tool_auth.check("anything_at_all", {}, "c", env={}) is None
    assert tool_auth.check("self_heal_promote", {}, "c", env={"REALAI_TOOLS_AUTH": "0"}) is None


def test_no_token_401():
    code, body = tool_auth.check(ALLOWED, {}, "c", env=env())
    assert code == 401 and body["error"] == "unauthorized"


def test_wrong_token_401():
    code, _ = tool_auth.check(ALLOWED, hdr("FAKE-wrong"), "c", env=env())
    assert code == 401


def test_non_bearer_scheme_401():
    code, _ = tool_auth.check(ALLOWED, {"Authorization": "Basic " + FAKE}, "c", env=env())
    assert code == 401


def test_right_token_allowed():
    assert tool_auth.check(ALLOWED, hdr(), "c", env=env()) is None


def test_non_allowlisted_403():
    code, body = tool_auth.check("self_heal_promote", hdr(), "c", env=env())
    assert code == 403 and body["error"] == "tool_not_allowed"


def test_default_allowlist_has_partial_abilities():
    allow = tool_auth.default_allowlist()
    assert "ability.pr_triage" in allow
    assert "list_agents" in allow


def test_allow_override():
    e = env(REALAI_TOOLS_ALLOW="foo, bar")
    assert tool_auth.check("foo", hdr(), "c", env=e) is None
    assert tool_auth.check(ALLOWED, hdr(), "c", env=e)[0] == 403


def test_flag_on_no_token_configured_503():
    code, body = tool_auth.check(ALLOWED, hdr(), "c", env=env(REALAI_TOOLS_TOKEN=None))
    assert code == 503 and "REALAI_TOOLS_TOKEN" in body["message"]
    code, _ = tool_auth.check(ALLOWED, hdr(), "c", env=env(REALAI_TOOLS_TOKEN=""))
    assert code == 503


def test_rate_limit_per_client():
    e = env(REALAI_TOOLS_RATE="3", REALAI_TOOLS_RATE_WINDOW="60")
    for _ in range(3):
        assert tool_auth.check(ALLOWED, hdr(), "a", env=e) is None
    assert tool_auth.check(ALLOWED, hdr(), "a", env=e)[0] == 429
    assert tool_auth.check(ALLOWED, hdr(), "b", env=e) is None


def test_rate_window_resets():
    rl = tool_auth.RateLimiter(limit=1, window=10)
    assert rl.allow("x", now=0)
    assert not rl.allow("x", now=5)
    assert rl.allow("x", now=11)


def test_token_never_logged(caplog):
    caplog.set_level(logging.DEBUG)
    tool_auth.check(ALLOWED, hdr(), "c", env=env())
    tool_auth.check(ALLOWED, hdr("FAKE-wrong-token-xyz"), "c", env=env())
    tool_auth.check("self_heal_promote", hdr(), "c", env=env())
    text = caplog.text
    assert "ability=list_agents" in text and "client=c" in text
    assert FAKE not in text and "FAKE-wrong-token-xyz" not in text


def test_route_is_wired():
    from pathlib import Path

    src = (Path(__file__).resolve().parents[1] / "realai" / "orchestration" / "v3_orchestrator.py").read_text(
        encoding="utf-8"
    )
    i = src.index('if path == "/v1/tools/execute":')
    assert "_tool_auth.check(" in src[i : i + 1500]
