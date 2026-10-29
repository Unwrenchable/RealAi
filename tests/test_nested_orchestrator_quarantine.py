"""Quarantined nested orchestrator copies must never start a server."""
import importlib.util
import socket
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    ROOT / "realai" / "orchestrators" / "nested_realai_v3_orchestrator.py",
    ROOT / "modules" / "orchestrators" / "nested_realai_v3_orchestrator.py",
]


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("path", FILES, ids=["realai", "modules"])
def test_main_exits_nonzero_without_binding(path, monkeypatch, capsys):
    mod = _load(path, "nested_q_" + path.parent.parent.name)

    def no_server(*a, **k):
        raise AssertionError("quarantined main() tried to start a server")

    monkeypatch.setattr(mod, "ThreadingHTTPServer", no_server)
    port = _free_port()
    rc = mod.main(["--host", "127.0.0.1", "--port", str(port)])
    assert rc != 0
    assert "realai/orchestration/v3_orchestrator.py" in capsys.readouterr().err
    with socket.socket() as s:  # port is still free
        s.bind(("127.0.0.1", port))


@pytest.mark.parametrize("path", FILES, ids=["realai", "modules"])
def test_dunder_main_exits_nonzero(path):
    port = _free_port()
    r = subprocess.run([sys.executable, str(path), "--port", str(port)], cwd=str(ROOT),
                       capture_output=True, text=True, timeout=120)
    assert r.returncode != 0
    assert "realai/orchestration/v3_orchestrator.py" in r.stderr
    with socket.socket() as s:
        s.bind(("127.0.0.1", port))
