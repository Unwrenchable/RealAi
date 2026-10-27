"""convert_to_gguf must run llama.cpp's converter without PYTHONSAFEPATH (it imports a sibling package)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import train_to_chat_gguf as t2g  # noqa: E402
import realai.training.llama_tools as lt  # noqa: E402


def test_converter_env_drops_pythonsafepath(monkeypatch):
    monkeypatch.setenv("PYTHONSAFEPATH", "1")
    monkeypatch.setenv("REALAI_HOME", "/x")
    env = t2g.converter_env()
    assert "PYTHONSAFEPATH" not in env and env["REALAI_HOME"] == "/x"
    import os

    assert os.environ["PYTHONSAFEPATH"] == "1"  # the caller's own env is untouched


def test_convert_to_gguf_runs_converter_without_safepath(tmp_path, monkeypatch):
    monkeypatch.setenv("PYTHONSAFEPATH", "1")
    monkeypatch.setattr(lt, "find_convert_hf_script", lambda *a, **k: tmp_path / "convert_hf_to_gguf.py")
    monkeypatch.setattr(lt, "python_for_llama_convert", lambda *a, **k: sys.executable)
    seen = []

    def fake_run(cmd, **kw):
        seen.append(kw.get("env"))
        Path(cmd[cmd.index("--outfile") + 1]).write_bytes(b"GGUF")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(t2g.subprocess, "run", fake_run)
    out = t2g.convert_to_gguf(tmp_path / "merged", tmp_path / "gguf" / "m-f16.gguf")
    assert out.is_file()
    assert seen and seen[0] is not None and "PYTHONSAFEPATH" not in seen[0]
