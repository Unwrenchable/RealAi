"""S2: local servers and llama launchers default to 127.0.0.1 (opt-in env for LAN)."""

from __future__ import annotations

import re
from pathlib import Path

import importlib

app_mod = importlib.import_module("realai.server.app")
import sys  # noqa: E402

app_mod = sys.modules["realai.server.app"]

ROOT = Path(__file__).resolve().parents[1]


def _capture(monkeypatch):
    seen = {}

    class _Srv:
        def serve_forever(self):
            return None

    def fake_make_server(host, port, wsgi):
        seen["host"], seen["port"] = host, port
        return _Srv()

    monkeypatch.setattr(app_mod, "make_server", fake_make_server)
    return seen


def test_server_app_defaults_to_loopback(monkeypatch):
    monkeypatch.delenv("REALAI_SERVER_HOST", raising=False)
    seen = _capture(monkeypatch)
    app_mod.main()
    assert seen == {"host": "127.0.0.1", "port": 8000}


def test_server_app_env_opt_in(monkeypatch):
    monkeypatch.setenv("REALAI_SERVER_HOST", "0.0.0.0")
    seen = _capture(monkeypatch)
    app_mod.main()
    assert seen["host"] == "0.0.0.0"


def test_explicit_host_wins(monkeypatch):
    monkeypatch.delenv("REALAI_SERVER_HOST", raising=False)
    seen = _capture(monkeypatch)
    app_mod.main("localhost", 9000)
    assert seen == {"host": "localhost", "port": 9000}


LAUNCHERS = [
    "scripts/windows/start_gpu_chat.bat",
    "scripts/run_local_selfheal.ps1",
    "scripts/start_v3_stack.ps1",
    "realai/server/app.py",
]


def test_launchers_have_no_hardcoded_wildcard_bind():
    for rel in LAUNCHERS:
        text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
        code = "\n".join(l for l in text.splitlines() if not re.match(r"\s*(#|REM |::)", l, re.I))
        assert not re.search(r"""--host["',\s]+0\.0\.0\.0|host\s*=\s*['"]0\.0\.0\.0""", code), rel
        assert "127.0.0.1" in text, rel
