"""Smoke tests for RealAI Hive CLI (no live stack required for unit bits)."""
from __future__ import annotations

import json

from click.testing import CliRunner

from realai.cli.hive.app import cli
from realai.cli.hive.format import table, truncate


def test_truncate():
    assert truncate("abc", 10) == "abc"
    assert truncate("abcdefghijklmnop", 8).endswith("…")


def test_table():
    out = table([["a", "b"]], headers=["H1", "H2"])
    assert "H1" in out and "a" in out


def test_version():
    runner = CliRunner()
    result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert "Hive CLI" in result.output


def test_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "agents" in result.output
    assert "multi" in result.output
    assert "stack" in result.output
    assert "learn" in result.output.lower()


def test_learn_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["learn", "--help"])
    assert result.exit_code == 0
    out = result.output
    low = out.lower()
    assert "local folder" in low
    assert "git url" in low or "git_url" in low
    assert r"C:\path\to\folder" in out or "C:\\path\\to\\folder" in out


def test_default_invokes_status_shape():
    runner = CliRunner()
    result = runner.invoke(cli, [])
    # May be down without stack, but must print Hive identity
    assert "RealAI Hive" in result.output
    assert result.exit_code == 0
