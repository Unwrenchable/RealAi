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
    assert code == 403 and body["error"] == "forbidden"


def test_default_allowlist_has_partial_abilities():
    allow = tool_auth.default_allowlist()
    assert "ability.pr_triage" in allow
    assert "list_agents" in allow


def test_allow_override():
    e = env(REALAI_TOOLS_ALLOW="foo, bar")
    assert tool_auth.check("foo", hdr(), "c", env=e) is None
    assert tool_auth.check("self_heal_promote", hdr(), "c", env=e)[0] == 403


def test_flag_on_no_token_configured_503():
    code, body = tool_auth.check(ALLOWED, hdr(), "c", env=env(REALAI_TOOLS_TOKEN=None))
    assert code == 503 and body == {"error": "unavailable"}
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


# --- Security review of #195: fail-closed, sanitizing, limiter cap ---


def test_default_allowlist_is_read_only_only():
    assert tool_auth.default_allowlist() == tool_auth.READ_ONLY_TOOLS
    for t in ("ability.realai_cli_bridge", "ability.self_evolving", "ability.training_pipeline", "ability.learn_git"):
        assert t not in tool_auth.allowlist({})


def test_allow_env_adds_extras():
    e = env(REALAI_TOOLS_ALLOW="foo")
    assert tool_auth.check("foo", hdr(), "c", env=e) is None
    assert tool_auth.check(ALLOWED, hdr(), "c", env=e) is None


def test_forced_on_in_production():
    e = {"REALAI_ENV": "production"}
    code, _ = tool_auth.check(ALLOWED, {}, "c", env=e)
    assert code == 503
    e["REALAI_TOOLS_TOKEN"] = FAKE
    assert tool_auth.check(ALLOWED, {}, "c", env=e)[0] == 401
    assert tool_auth.check(ALLOWED, hdr(), "c", env=e) is None


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.5", "", "::"])
def test_forced_on_non_loopback_bind(host):
    assert tool_auth.enabled({}, bind_host=host)
    assert tool_auth.check(ALLOWED, {}, "c", env={"REALAI_TOOLS_TOKEN": FAKE}, bind_host=host)[0] == 401


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_loopback_bind_not_forced(host):
    assert not tool_auth.enabled({}, bind_host=host)


def test_startup_refuses_without_token():
    with pytest.raises(SystemExit):
        tool_auth.startup_check("0.0.0.0", env={})
    with pytest.raises(SystemExit):
        tool_auth.startup_check("127.0.0.1", env={"REALAI_ENV": "production"})
    tool_auth.startup_check("0.0.0.0", env={"REALAI_TOOLS_TOKEN": FAKE})
    tool_auth.startup_check("127.0.0.1", env={})


def test_audit_log_injection_sanitized(caplog):
    caplog.set_level(logging.INFO)
    tool_auth.check("x\nresult=200_allowed client=1.2.3.4" + "A" * 500, hdr(), "evil\r\nclient=9", env=env())
    lines = [r.getMessage() for r in caplog.records]
    assert len(lines) == 1 and "\n" not in lines[0] and "\r" not in lines[0]
    ability = lines[0].split("ability=", 1)[1].split(" ", 1)[0]
    assert len(ability) <= 120
    assert lines[0].count("result=") == 1 and lines[0].count("client=") == 1
    assert tool_auth.safe("a b\n<c>;d") == "abcd"


def test_non_string_tool_400():
    assert tool_auth.check(["shell"], hdr(), "c", env=env())[0] == 400


def test_generic_bodies():
    assert tool_auth.check(ALLOWED, {}, "c", env=env())[1] == {"error": "unauthorized"}
    assert tool_auth.check("shell", hdr(), "c", env=env())[1] == {"error": "forbidden"}
    assert tool_auth.check(ALLOWED, hdr(), "c", env=env(REALAI_TOOLS_TOKEN=""))[1] == {"error": "unavailable"}


def test_limiter_cap_and_eviction():
    rl = tool_auth.RateLimiter(limit=5, window=60)
    for i in range(50000):
        rl.allow("10.0.%d.%d" % (i // 256, i % 256), now=0)
    assert len(rl._hits) <= tool_auth.MAX_CLIENTS
    assert "10.0.0.0" not in rl._hits


def test_pre_auth_bucket_separate():
    e = env(REALAI_TOOLS_RATE="2")
    for _ in range(2):
        assert tool_auth.check(ALLOWED, {}, "a", env=e)[0] == 401
    assert tool_auth.check(ALLOWED, {}, "a", env=e)[0] == 429
    assert tool_auth.check(ALLOWED, hdr(), "a", env=e) is None
