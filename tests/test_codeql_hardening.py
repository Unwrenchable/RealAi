"""Regression tests for the CodeQL hardening (path containment, argv, error leaks)."""
import os

from realai.server import llama_cli_backend as lcb


def test_llama_rejects_non_allowlisted_model(tmp_path, monkeypatch):
    rogue = tmp_path / "rogue.gguf"
    rogue.write_text("x")
    monkeypatch.setattr(lcb, "_allowed_model_files", lambda: [])
    assert lcb._allowed_model_file(str(rogue)) is None
    assert lcb._allowed_model_file("--help") is None
    assert lcb._allowed_model_file("") is None


def test_llama_accepts_allowlisted_model(tmp_path, monkeypatch):
    good = tmp_path / "m.gguf"
    good.write_text("x")
    real = os.path.realpath(str(good))
    monkeypatch.setattr(lcb, "_allowed_model_files", lambda: [real])
    assert lcb._allowed_model_file(str(good)) == real


def test_workspace_catalog_rejects_outside_home(tmp_path, monkeypatch):
    monkeypatch.setenv("REALAI_HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir()
    from realai.plugins.workspace_info import workspace_catalog

    out = workspace_catalog(str(tmp_path))
    assert out["ok"] is False
    out = workspace_catalog(str(tmp_path / "home" / ".." / ".."))
    assert out["ok"] is False
