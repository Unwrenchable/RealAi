"""Model / llama-cli discovery ported from RealAi-unified (no real models needed)."""
from realai.server import local_discovery as ld


def test_resolve_model_path_finds_relative_name(tmp_path):
    (tmp_path / "sub").mkdir()
    gguf = tmp_path / "sub" / "tiny.gguf"
    gguf.write_bytes(b"x")
    assert ld.resolve_model_path("tiny.gguf", roots=[tmp_path]) == str(gguf)
    assert ld.resolve_model_path("/nope/missing.gguf", roots=[tmp_path]) is None
    assert ld.resolve_model_path(None) is None


def test_discover_model_path_honours_env(tmp_path, monkeypatch):
    f = tmp_path / "m.gguf"
    f.write_bytes(b"x")
    monkeypatch.setenv("REALAI_MODEL_PATH", str(f))
    assert ld.discover_model_path() == str(f)


def test_discover_llama_cli_honours_env(tmp_path, monkeypatch):
    exe = tmp_path / "llama-cli"
    exe.write_text("#!/bin/sh\n")
    monkeypatch.setenv("REALAI_LLAMA_CLI_PATH", str(exe))
    assert ld.discover_llama_cli() == str(exe)
