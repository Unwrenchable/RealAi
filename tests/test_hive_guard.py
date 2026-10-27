"""Tests for the Hive v3 inbound guard (realai/orchestration/hive_guard.py)."""

from __future__ import annotations

import http.client
import json
import os
import threading
from http.server import ThreadingHTTPServer

import pytest

import realai.orchestration.v3_orchestrator as orch

guard = orch._hive_guard

GUARD_ENV = (
    "REALAI_HIVE_GUARD",
    "REALAI_ALLOWED_HOSTS",
    "REALAI_ALLOWED_ORIGINS",
    "REALAI_MAX_BODY_BYTES",
    "REALAI_MAX_AUDIO_BODY_BYTES",
    "REALAI_RATE_LIMIT",
    "REALAI_PRIV_RATE_LIMIT",
    "REALAI_HIVE_TOKEN_MODE",
    "REALAI_HIVE_TOKEN_FILE",
)


@pytest.fixture
def hive(monkeypatch, tmp_path):
    for k in GUARD_ENV:
        monkeypatch.delenv(k, raising=False)
    monkeypatch.setenv("REALAI_HIVE_TOKEN_FILE", str(tmp_path / "hive_token"))
    guard._reset_for_tests()
    servers = []

    def start(**env):
        for k, v in env.items():
            monkeypatch.setenv(k, str(v))
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), orch.Handler)
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        servers.append(httpd)
        return httpd.server_address[1]

    yield start
    for s in servers:
        s.shutdown()
        s.server_close()
    guard._reset_for_tests()


def req(port, method, path, body=None, headers=None, host=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
    data = None
    if body is not None:
        data = body if isinstance(body, (bytes, bytearray)) else json.dumps(body).encode()
    conn.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
    conn.putheader("Host", host or f"127.0.0.1:{port}")
    hdrs = dict(headers or {})
    if data is not None:
        hdrs.setdefault("Content-Type", "application/json")
        hdrs["Content-Length"] = str(len(data))
    for k, v in hdrs.items():
        conn.putheader(k, v)
    conn.endheaders(data)
    r = conn.getresponse()
    raw = r.read()
    conn.close()
    try:
        obj = json.loads(raw.decode() or "null")
    except Exception:
        obj = None
    return r.status, r.getheaders(), obj


# ---------------------------------------------------------------- Host / Origin


def test_forged_host_rejected(hive):
    port = hive()
    code, _, obj = req(port, "GET", "/no-such-page", host="evil.example:8001")
    assert code == 421 and obj["error"] == "host_not_allowed"


@pytest.mark.parametrize("host", ["127.0.0.1:{p}", "localhost:{p}", "[::1]:{p}", "localhost"])
def test_loopback_hosts_pass(hive, host):
    port = hive()
    code, _, obj = req(port, "GET", "/no-such-page", host=host.format(p=port))
    assert code == 404 and obj["error"] == "not_found"


def test_extra_allowed_host_env(hive):
    port = hive(REALAI_ALLOWED_HOSTS="realai.lan")
    assert req(port, "GET", "/x", host="realai.lan:8001")[0] == 404


def test_foreign_origin_post_rejected(hive):
    port = hive()
    for origin in ("https://evil.example", "null", "http://127.0.0.1:9999"):
        code, _, obj = req(port, "POST", "/v1/nope", {}, {"Origin": origin})
        assert code == 403 and obj["error"] == "origin_not_allowed", origin


@pytest.mark.parametrize(
    "origin",
    [
        "http://127.0.0.1:{p}",  # same-origin console / fusion-ui / agents-ui / voice-lab
        "http://localhost:{p}",
        "http://127.0.0.1:3000",  # Next frontend
        "http://localhost:3000",
        "http://127.0.0.1:8787",  # Voice Studio
        "http://localhost:8787",
        "http://127.0.0.1:5173",
        "vscode-webview://abc123",
    ],
)
def test_allowlisted_origins_post(hive, origin):
    port = hive()
    o = origin.format(p=port)
    code, headers, obj = req(port, "POST", "/v1/nope", {}, {"Origin": o})
    assert code == 404 and obj["error"] == "not_found"
    assert dict(headers).get("Access-Control-Allow-Origin") == o


def test_preflight_from_voice_studio_allows_token_header(hive):
    port = hive()
    code, headers, _ = req(port, "OPTIONS", "/v1/chat/completions", headers={"Origin": "http://127.0.0.1:8787"})
    h = dict(headers)
    assert code == 204
    assert h["Access-Control-Allow-Origin"] == "http://127.0.0.1:8787"
    assert "X-RealAI-Token" in h["Access-Control-Allow-Headers"]


def test_foreign_origin_gets_pinned_cors(hive):
    port = hive()
    _, headers, _ = req(port, "GET", "/x", headers={"Origin": "https://evil.example"})
    assert dict(headers)["Access-Control-Allow-Origin"] == f"http://127.0.0.1:8001"


# ------------------------------------------------------------ body / JSON / size


def test_non_json_post_rejected(hive):
    port = hive()
    for ctype in ("text/plain", "application/x-www-form-urlencoded", "multipart/form-data; boundary=x"):
        code, _, obj = req(port, "POST", "/v1/nope", b"a=b", {"Content-Type": ctype})
        assert code == 415 and obj["error"] == "json_only", ctype


def test_unlabeled_body_from_browser_rejected_but_ok_from_cli(hive):
    port = hive()
    # http.client: no Content-Type at all
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    for origin, expect in (("http://127.0.0.1:3000", 415), (None, 404)):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
        conn.putrequest("POST", "/v1/nope")
        conn.putheader("Content-Length", "2")
        if origin:
            conn.putheader("Origin", origin)
        conn.endheaders(b"{}")
        assert conn.getresponse().status == expect
        conn.close()


def test_json_variants_accepted(hive):
    port = hive()
    for ctype in ("application/json", "application/json; charset=utf-8", "application/vnd.x+json"):
        assert req(port, "POST", "/v1/nope", b"{}", {"Content-Type": ctype})[0] == 404


def test_oversize_body_rejected(hive):
    port = hive(REALAI_MAX_BODY_BYTES=64)
    code, _, obj = req(port, "POST", "/v1/nope", {"x": "y" * 200})
    assert code == 413 and obj["error"] == "body_too_large"


def test_audio_route_has_larger_cap(hive):
    port = hive(REALAI_MAX_BODY_BYTES=64, REALAI_MAX_AUDIO_BODY_BYTES=10_000)
    cfg = guard.GuardConfig(server_port=port)
    assert cfg.body_cap("/v1/audio/transcriptions") == 10_000
    assert cfg.body_cap("/v1/chat/completions") == 64


# ------------------------------------------------------------------ rate limit


def test_rate_limit(hive):
    port = hive(REALAI_RATE_LIMIT=3)
    codes = [req(port, "POST", "/v1/nope", {})[0] for _ in range(5)]
    assert codes[:3] == [404, 404, 404]
    assert codes[3:] == [429, 429]


def test_gets_not_rate_limited(hive):
    port = hive(REALAI_RATE_LIMIT=1)
    assert [req(port, "GET", "/x")[0] for _ in range(4)] == [404] * 4


# ---------------------------------------------------------------- token mode


PRIV = [
    "/v1/tools/execute",
    "/v1/abilities/run",
    "/v1/craft",
    "/v1/hive",
    "/v1/agents/run",
    "/v1/agents/simulation",
    "/v1/multi-agent/run",
    "/v1/recovery/promote",
    "/v1/learn/promote",
    "/v1/self-heal/promote",
    "/v1/self-heal/cycle",
]


def test_token_mode_off_by_default_no_file(hive, tmp_path):
    port = hive()
    req(port, "GET", "/console")
    assert not (tmp_path / "hive_token").exists()


@pytest.mark.parametrize("path", PRIV)
def test_token_mode_refuses_privileged_without_token(hive, path):
    port = hive(REALAI_HIVE_TOKEN_MODE=1)
    code, _, obj = req(port, "POST", path, {})
    assert code == 401 and obj["error"] == "token_required"


def test_token_never_in_refusal_body(hive, tmp_path):
    port = hive(REALAI_HIVE_TOKEN_MODE=1)
    _, _, obj = req(port, "POST", "/v1/tools/execute", {})
    tok = (tmp_path / "hive_token").read_text().strip()
    assert len(tok) >= 32
    assert tok not in json.dumps(obj)


def test_token_file_created_owner_only(hive, tmp_path):
    hive(REALAI_HIVE_TOKEN_MODE=1)
    tok = guard.load_or_create_token()
    p = tmp_path / "hive_token"
    assert p.read_text().strip() == tok
    if os.name != "nt":
        assert (p.stat().st_mode & 0o077) == 0
    # stable across calls / restarts
    guard._reset_for_tests()
    assert guard.load_or_create_token() == tok


@pytest.mark.parametrize("style", ["header", "bearer", "cookie"])
def test_token_accepted(hive, style):
    port = hive(REALAI_HIVE_TOKEN_MODE=1)
    tok = guard.load_or_create_token()
    h = {
        "header": {"X-RealAI-Token": tok},
        "bearer": {"Authorization": "Bearer " + tok},
        "cookie": {"Cookie": f"other=1; {guard.COOKIE_NAME}={tok}"},
    }[style]
    cfg = guard.GuardConfig(server_port=port)
    assert guard.check_request(cfg, "POST", "/v1/tools/execute", {**h, "Content-Length": "2", "Content-Type": "application/json"}, "127.0.0.1").ok


def test_wrong_token_refused(hive):
    port = hive(REALAI_HIVE_TOKEN_MODE=1)
    code, _, _ = req(port, "POST", "/v1/craft", {}, {"X-RealAI-Token": "wrong-token-value-xxxxxxxx"})
    assert code == 401


def test_non_privileged_route_open_in_token_mode(hive):
    port = hive(REALAI_HIVE_TOKEN_MODE=1)
    assert req(port, "POST", "/v1/nope", {})[0] == 404


def test_console_page_sets_httponly_cookie(hive, tmp_path):
    port = hive(REALAI_HIVE_TOKEN_MODE=1)
    _, headers, _ = req(port, "GET", "/console")
    cookies = [v for k, v in headers if k.lower() == "set-cookie"]
    assert cookies, headers
    c = cookies[0]
    assert c.startswith(guard.COOKIE_NAME + "=")
    assert "HttpOnly" in c and "SameSite=Strict" in c
    # API responses do not carry the cookie
    _, headers2, _ = req(port, "GET", "/x")
    assert not [v for k, v in headers2 if k.lower() == "set-cookie"]


def test_chat_live_exec_dispatch_skipped_without_token(hive, monkeypatch):
    calls = []

    def fake_dispatch(text):
        calls.append(text)
        return {"surface": "operator", "result": {"ok": True}}

    def fake_proxy(method, path, data, headers):
        return 200, {}, json.dumps({"choices": [{"index": 0, "message": {"role": "assistant", "content": "plain"}}]}).encode()

    monkeypatch.setattr(orch, "_chat_operator_dispatch", fake_dispatch)
    monkeypatch.setattr(orch, "_proxy", fake_proxy)
    port = hive(REALAI_HIVE_TOKEN_MODE=1)
    body = {"model": "x", "messages": [{"role": "user", "content": "zzqx probe 4471"}]}
    code, _, obj = req(port, "POST", "/v1/chat/completions", body, {"X-RealAI-Tools": "1"})
    assert code == 200 and calls == []
    assert (obj or {}).get("id") != "realai-operator"

    tok = guard.load_or_create_token()
    code, _, obj = req(port, "POST", "/v1/chat/completions", body, {"X-RealAI-Tools": "1", "X-RealAI-Token": tok})
    assert code == 200 and calls == ["zzqx probe 4471"]
    assert obj["id"] == "realai-operator"


# ----------------------------------------------------------------- kill switch


def test_guard_disable_switch(hive):
    port = hive(REALAI_HIVE_GUARD=0)
    assert req(port, "GET", "/x", host="evil.example")[0] == 404
    assert req(port, "POST", "/v1/nope", b"a", {"Content-Type": "text/plain", "Origin": "https://evil.example"})[0] == 404


def test_is_privileged_matrix():
    for p in PRIV + ["/v1/tools/execute/", "/v1/self-heal/assemble"]:
        assert guard.is_privileged(p), p
    for p in ("/v1/chat/completions", "/v1/audio/speech", "/health", "/v1/self-healx"):
        assert not guard.is_privileged(p), p


def test_rate_limit_off_by_default(hive):
    port = hive()
    cfg = guard.GuardConfig(server_port=port)
    assert cfg.rate_limit == 0 and cfg.priv_rate_limit == 0 and cfg.token_mode is False
    assert all(req(port, "POST", "/v1/nope", {})[0] == 404 for _ in range(30))


def test_host_origin_on_by_default(hive):
    port = hive()
    assert guard.GuardConfig(server_port=port).enabled is True
