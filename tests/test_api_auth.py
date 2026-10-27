"""Service-key gate for python -m realai.api_server (REALAI_API_KEY)."""
from __future__ import annotations

import hmac
import json

import pytest

pytest.importorskip("pydantic")

from realai.cloud_fallback import _HOSTED_ENV_MARKERS
from realai.server.api_auth import (
    auth_startup_message,
    authorize,
    bearer_for_provider,
    client_key,
    constant_time_key_match,
    parse_configured_keys,
)
from realai.server.legacy_bridge import call
from realai.server.server_settings import ServerSettings


SECRET = "gate-secret-do-not-log"
OTHER = "second-gate-key"
WRONG = "wrong-key-do-not-echo"


@pytest.fixture
def locked(monkeypatch):
    """Production, not a hosted marker, no key unless a test sets one."""
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("REALAI_API_KEY", "")
    for name in _HOSTED_ENV_MARKERS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_parse_comma_separated_keys_strips_quotes_and_blanks():
    assert parse_configured_keys(' alpha , "beta" , , \'gamma\' ') == ["alpha", "beta", "gamma"]
    assert parse_configured_keys("") == []
    assert parse_configured_keys(None) == []


def test_constant_time_match_checks_every_key(monkeypatch):
    calls = {"n": 0}
    real = hmac.compare_digest

    def wrapped(a, b):
        calls["n"] += 1
        return real(a, b)

    monkeypatch.setattr("realai.server.api_auth.hmac.compare_digest", wrapped)
    assert constant_time_key_match("bbbb", ["aaaa", "bbbb", "cccc"]) is True
    assert calls["n"] == 3
    assert constant_time_key_match("bb", ["bbbb"]) is False
    assert constant_time_key_match("bbbbx", ["bbbb"]) is False
    assert constant_time_key_match("", ["bbbb"]) is False


def test_health_is_open_and_api_routes_require_a_key(locked):
    status, data, _ = call("GET", "/health")
    assert status == 200
    assert data["status"] == "ok"

    status, data, _ = call("GET", "/v1/models")
    assert status == 401
    assert data["error"]["type"] == "server_error"
    assert data["error"]["code"] == "api_key_not_configured"
    assert "REALAI_API_KEY" in data["error"]["message"]
    assert SECRET not in json.dumps(data)

    status, _, ctype = call("GET", "/")
    assert status == 200
    assert "html" in ctype

    status, body, _ = call("OPTIONS", "/v1/models")
    assert status == 200


def test_bearer_and_x_api_key_accept_any_configured_key(locked, monkeypatch):
    monkeypatch.setenv("REALAI_API_KEY", "{0}, {1}".format(SECRET, OTHER))

    missing, missing_body, _ = call("GET", "/v1/models")
    assert missing == 401
    assert missing_body["error"]["code"] == "invalid_api_key"
    assert missing_body["error"]["message"].startswith("Missing API key")

    wrong, wrong_body, _ = call("GET", "/v1/models", headers={"Authorization": "Bearer " + WRONG})
    assert wrong == 401
    assert wrong_body["error"]["code"] == "invalid_api_key"
    assert wrong_body["error"]["message"] == "Incorrect API key provided."
    assert WRONG not in json.dumps(wrong_body)
    assert SECRET not in json.dumps(wrong_body)

    # A cloud-looking key is still rejected when it is not the service key.
    spoof, _, _ = call("GET", "/v1/models", headers={"Authorization": "Bearer sk-not-the-service-key"})
    assert spoof == 401

    ok, payload, _ = call("GET", "/v1/models", headers={"Authorization": "bearer " + OTHER})
    assert ok == 200
    assert isinstance(payload, dict)

    ok_x, _, _ = call("GET", "/v1/models", headers={"X-API-Key": SECRET})
    assert ok_x == 200

    # Provider metadata is an API route. Static fusion shell is not.
    denied, _, _ = call("GET", "/ui/providers")
    assert denied == 401
    status, shell, shell_type = call("GET", "/fusion-ui/config.js")
    assert status == 200
    assert "javascript" in shell_type
    text = shell if isinstance(shell, str) else json.dumps(shell)
    assert SECRET not in text
    assert OTHER not in text
    assert '"API_KEY": ""' in text or '"API_KEY":""' in text


def test_post_and_delete_are_gated_before_the_handler(locked, monkeypatch):
    monkeypatch.setenv("REALAI_API_KEY", SECRET)
    status, body, _ = call(
        "POST",
        "/v1/chat/completions",
        {"model": "realai-1.0", "messages": [{"role": "user", "content": "hi"}]},
    )
    assert status == 401
    assert "choices" not in body
    assert body["error"]["code"] == "invalid_api_key"
    assert "hi" not in json.dumps(body)

    status, _, _ = call("DELETE", "/v1/memory/forget", {"item_id": "x"})
    assert status == 401


def test_fail_closed_on_render_even_if_env_says_development(locked, monkeypatch):
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("RENDER", "true")
    monkeypatch.setenv("REALAI_API_KEY", "")
    status, body, _ = call("GET", "/v1/models")
    assert status == 401
    assert body["error"]["code"] == "api_key_not_configured"


def test_development_without_a_key_stays_open(locked, monkeypatch):
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("REALAI_API_KEY", "")
    status, _, _ = call("GET", "/v1/models")
    assert status == 200


def test_configured_key_is_required_even_in_development(locked, monkeypatch):
    monkeypatch.setenv("ENV", "development")
    monkeypatch.setenv("REALAI_API_KEY", SECRET)
    assert call("GET", "/v1/models")[0] == 401
    assert call("GET", "/v1/models", headers={"X-API-Key": SECRET})[0] == 200


def test_startup_log_and_public_settings_omit_key_material(locked, monkeypatch):
    monkeypatch.setenv("REALAI_API_KEY", SECRET + "," + OTHER)
    message = auth_startup_message()
    assert "2 keys" in message
    assert SECRET not in message
    assert OTHER not in message

    monkeypatch.setenv("REALAI_API_KEY", "")
    closed = auth_startup_message()
    assert "fail closed" in closed
    assert "not set" in closed

    snapshot = ServerSettings(REALAI_API_KEY=SECRET, OPENAI_API_KEY="sk-provider", ENV="production")
    public = snapshot.public_dict()
    assert public["REALAI_API_KEY_SET"] is True
    assert public["OPENAI_API_KEY_SET"] is True
    assert SECRET not in json.dumps(public)
    assert "sk-provider" not in json.dumps(public)


def test_service_bearer_is_not_forwarded_as_provider_key(locked, monkeypatch):
    monkeypatch.setenv("REALAI_API_KEY", SECRET)
    assert bearer_for_provider("Bearer " + SECRET) is None
    assert bearer_for_provider("Bearer sk-live-provider") == "sk-live-provider"
    monkeypatch.setenv("REALAI_API_KEY", "sk-shared-service")
    assert bearer_for_provider("Bearer sk-shared-service") == "sk-shared-service"
    assert client_key() == "sk-shared-service"


def test_get_model_keeps_provider_bearer_beside_x_api_key(locked, monkeypatch):
    monkeypatch.setenv("REALAI_API_KEY", SECRET)
    from realai.server import legacy_api

    captured = {}

    class FakeRealAI(object):
        def __init__(self, model_name=None, api_key=None, provider=None, base_url=None):
            captured["model_name"] = model_name
            captured["api_key"] = api_key
            captured["provider"] = provider

    monkeypatch.setattr(legacy_api, "RealAI", FakeRealAI)
    handler = legacy_api.RealAIAPIHandler.__new__(legacy_api.RealAIAPIHandler)
    handler.headers = {
        "Authorization": "Bearer sk-provider-key",
        "X-API-Key": SECRET,
        "X-Provider": "openai",
    }
    handler._get_model("realai-1.0")
    assert captured["api_key"] == "sk-provider-key"

    handler.headers = {"Authorization": "Bearer " + SECRET, "X-Provider": "realai"}
    captured.clear()
    handler._get_model("realai-1.0")
    assert captured["api_key"] != SECRET


def test_authorize_unit_shapes():
    from realai.server.api_auth import is_public_request

    assert authorize("GET", "/health", authorization="").allowed is True
    assert is_public_request("GET", "/health") is True
    assert is_public_request("HEAD", "/health/") is True
    assert is_public_request("POST", "/health") is False
    assert is_public_request("GET", "/v1/models") is False
    assert is_public_request("OPTIONS", "/v1/chat/completions") is True
    assert is_public_request("GET", "/fusion-ui/index.html") is True
    assert is_public_request("GET", "/ui/providers") is False
