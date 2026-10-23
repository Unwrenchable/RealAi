"""Tests for hive wiring: :8001 provider w/ fallback, pytest sandbox, guarded endpoints, shims."""
from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from realai.agentx.hive import governance, hive_client, http_api
from realai.agentx.hive.overmind import Overmind


class _FakeHive(BaseHTTPRequestHandler):
    seen: list = []

    def log_message(self, *a):
        pass

    def _send(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        self._send({"status": "ok"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        _FakeHive.seen.append({"token": self.headers.get("X-RealAI-Token"), "body": body})
        self._send({"choices": [{"message": {"content": "hive says hi"}}], "model": "m"})


@pytest.fixture
def fake_hive(monkeypatch):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _FakeHive)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    monkeypatch.setenv("REALAI_HIVE_URL", f"http://127.0.0.1:{srv.server_address[1]}")
    _FakeHive.seen = []
    yield srv
    srv.shutdown()


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("REALAI_HOME", str(tmp_path))
    monkeypatch.setenv("REALAI_HIVE_TOKEN_FILE", str(tmp_path / "no_token"))
    for k in ("REALAI_HIVE_TOKEN", "REALAI_API_KEY", "REALAI_SANDBOX_CMD", "REALAI_SANDBOX_TESTS", "REALAI_DEFAULT_MODEL"):
        monkeypatch.delenv(k, raising=False)


def test_base_is_loopback_only(monkeypatch):
    monkeypatch.setenv("REALAI_HIVE_URL", "http://evil.example:8001")
    assert hive_client.hive_base() == hive_client.DEFAULT_BASE


def test_token_order_and_file(monkeypatch, tmp_path):
    f = tmp_path / "tok"
    f.write_text("from-file\n")
    monkeypatch.setenv("REALAI_HIVE_TOKEN_FILE", str(f))
    monkeypatch.setenv("REALAI_API_KEY", "local")
    assert hive_client.local_token() == "from-file"
    monkeypatch.setenv("REALAI_HIVE_TOKEN", "from-env")
    assert hive_client.local_token() == "from-env"


def test_overmind_uses_hive_when_up(fake_hive, monkeypatch):
    monkeypatch.setenv("REALAI_HIVE_TOKEN", "sekret")
    out = Overmind(use_hive=True).run("check the radio module", team_id="vault77")
    step = out["steps"][0]
    assert step["provider"] == "realai-hive" and step["fallback"] is False
    assert step["output"] == "hive says hi"
    assert _FakeHive.seen[0]["token"] == "sekret"
    assert "model" not in _FakeHive.seen[0]["body"]  # default model untouched
    assert "sekret" not in json.dumps(out)


def test_overmind_falls_back_when_hive_down(monkeypatch):
    monkeypatch.setenv("REALAI_HIVE_URL", "http://127.0.0.1:9")
    out = Overmind(use_hive=True).run("check the radio module", team_id="vault77")
    assert all(s["fallback"] and s["provider"] == "local" for s in out["steps"])


def _ws(tmp_path: Path, good: bool) -> Path:
    ws = tmp_path / "ws"
    (ws / "pkg").mkdir(parents=True)
    (ws / "tests").mkdir()
    (ws / "pkg" / "__init__.py").write_text("")
    (ws / "pkg" / "calc.py").write_text("def add(a, b):\n    return a + b\n")
    (ws / "tests" / "test_calc.py").write_text("from pkg.calc import add\n\ndef test_add():\n    assert add(2, 2) == 4\n")
    (ws / "tests" / "test_other.py").write_text("def test_never():\n    raise SystemExit('should not run')\n")
    return ws


@pytest.mark.parametrize("new,ok", [("return b + a", True), ("return a - b", False)])
def test_sandbox_runs_scoped_pytest_on_copy(tmp_path, monkeypatch, new, ok):
    ws = _ws(tmp_path, True)
    monkeypatch.setenv("REALAI_WORKSPACE", str(ws))
    change = {"args": {"file_path": "pkg/calc.py", "old_string": "return a + b", "new_string": new}}
    res = governance.default_sandbox(change)
    assert res["ok"] is ok, res
    assert res["tests"] == ["tests/test_calc.py"]
    assert "return a + b" in (ws / "pkg" / "calc.py").read_text()  # real workspace untouched


def test_sandbox_fails_closed_without_tests(tmp_path, monkeypatch):
    ws = _ws(tmp_path, True)
    (ws / "pkg" / "lonely.py").write_text("x = 1\n")
    monkeypatch.setenv("REALAI_WORKSPACE", str(ws))
    res = governance.default_sandbox({"file_path": "pkg/lonely.py", "old_string": "x = 1", "new_string": "x = 2"})
    assert res["ok"] is False and "no tests" in res["reason"]


def test_sandbox_timeout(tmp_path, monkeypatch):
    ws = _ws(tmp_path, True)
    (ws / "tests" / "test_calc.py").write_text("import time\n\ndef test_slow():\n    time.sleep(30)\n")
    monkeypatch.setenv("REALAI_WORKSPACE", str(ws))
    monkeypatch.setenv("REALAI_SANDBOX_TIMEOUT", "3")
    res = governance.default_sandbox({"file_path": "pkg/calc.py", "old_string": "return a + b", "new_string": "return a+b"})
    assert res["ok"] is False and "timeout" in res["reason"]


TOK = lambda: "t0ken"  # noqa: E731


def test_endpoints_require_loopback_and_token():
    assert http_api.handle("GET", "/v1/hive/teams", {}, {}, "10.0.0.5", {"X-RealAI-Token": "t0ken"}, TOK)[0] == 403
    assert http_api.handle("GET", "/v1/hive/teams", {}, {}, "127.0.0.1", {}, TOK)[0] == 401
    assert http_api.handle("GET", "/v1/hive/teams", {}, {}, "127.0.0.1", {"X-RealAI-Token": "nope"}, TOK)[0] == 401
    assert http_api.handle("GET", "/v1/hive/teams", {}, {}, "127.0.0.1", {"X-RealAI-Token": "x"}, lambda: "")[0] == 503


def test_endpoints_teams_run_playtest_findings(monkeypatch):
    monkeypatch.setenv("REALAI_AGENTX_USE_HIVE", "0")
    h = {"Authorization": "Bearer t0ken"}
    code, body = http_api.handle("GET", "/v1/hive/teams", {}, {}, "127.0.0.1", h, TOK)
    ids = {t["id"] for t in body["teams"]}
    assert code == 200 and {"vault77", "goon"} <= ids
    code, body = http_api.handle("POST", "/v1/hive/teams/vault77/run", {}, {"goal": "fix radio"}, "127.0.0.1", h, TOK)
    assert code == 200 and body["team"] == "vault77" and body["steps"]
    assert http_api.handle("POST", "/v1/hive/teams/nope/run", {}, {"goal": "x"}, "127.0.0.1", h, TOK)[0] == 404
    assert http_api.handle("POST", "/v1/hive/teams/vault77/run", {}, {}, "127.0.0.1", h, TOK)[0] == 400
    code, body = http_api.handle("POST", "/v1/hive/playtest", {}, {"team": "vault77"}, "127.0.0.1", h, TOK)
    assert code == 200 and body["team"] == "vault77"
    code, body = http_api.handle("GET", "/v1/hive/findings", {"team": ["vault77"]}, {}, "127.0.0.1", h, TOK)
    assert code == 200 and isinstance(body["findings"], list)


def test_findings_recorded(tmp_path):
    from realai.agentx.hive.playtest import read_findings, record_findings
    record_findings([{"team": "a", "task": "1"}, {"team": "b", "task": "2"}])
    assert [r["task"] for r in read_findings(team="a")] == ["1"]


def test_handles_paths():
    assert http_api.handles("/v1/hive/teams/vault77/run") and http_api.handles("/v1/hive/findings")
    assert not http_api.handles("/v1/hive")


def test_orchestrator_has_hive_hook_and_binds_loopback():
    import realai.orchestration.v3_orchestrator as v
    src = Path(v.__file__).read_text(encoding="utf-8")
    assert hasattr(v.Handler, "_agentx_hive")
    assert "0.0.0.0" not in src.split("def main", 1)[1].split("ThreadingHTTPServer(", 1)[0]


def test_agent_tools_and_hive_memory_forward():
    # Source-level checks: other suite tests may pre-stub agent_tools.* in sys.modules.
    root = Path(__file__).resolve().parents[1]
    for rel, canon in (("agent_tools/engine/memory.py", "realai.agentx.engine.memory"),
                       ("agent_tools/providers/router.py", "realai.agentx.providers.router"),
                       ("agent_tools/loader.py", "realai.agentx.engine.loader")):
        src = (root / rel).read_text(encoding="utf-8")
        assert f"from {canon} import *" in src
        assert (root / rel.replace(".py", "_legacy.py")).is_file()  # original kept
    assert "from realai.agentx.engine.memory import" in (root / "abilities/hive_memory.py").read_text(encoding="utf-8")
    # agent_tools/registry.py stays the recovered fork (has recommend_profile), not a shim.
    assert "def recommend_profile" in (root / "agent_tools/registry.py").read_text(encoding="utf-8")
