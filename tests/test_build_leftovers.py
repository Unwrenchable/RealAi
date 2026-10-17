"""Build-leftover fixes (docs/BUILD_LEFTOVERS.md): one install root, no stale trees in the wheel."""
from pathlib import Path

import tomllib

ROOT = Path(__file__).resolve().parents[1]


def test_no_in_package_setup_or_pyproject():
    for rel in ("realai/setup.py", "realai/pyproject.toml", "realai/plugins/setup.py",
                "realai/plugins/pyproject.toml", "realai/examples/setup.py"):
        assert not (ROOT / rel).exists(), rel


def test_pyproject_excludes_stale_trees():
    from setuptools import find_packages

    cfg = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    find = cfg["tool"]["setuptools"]["packages"]["find"]
    for pat in ("_parked*", "logs*", "*.learn_cache*", "realai.tests*", "recovered*", "_quarantine*"):
        assert pat in find["exclude"], pat
    pkgs = find_packages(where=str(ROOT), include=find["include"], exclude=find["exclude"])
    assert "realai" in pkgs and "realai.server" in pkgs
    assert not [p for p in pkgs if p.startswith(("_parked", "logs")) or "_archive_nest" in p or p.startswith("realai.tests")]


def test_root_entry_points_kept():
    cfg = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = cfg["project"]["scripts"]
    assert scripts["realai-server"] == "realai.server.app:main" and scripts["realai-craft"] == "realai.cli.craft:main"


def test_no_approvals_runtime_state_tracked():
    import subprocess

    out = subprocess.run(["git", "ls-files", "*.approvals.json*", ".approvals.json*"], cwd=ROOT,
                         capture_output=True, text=True).stdout
    assert out.strip() == ""
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".approvals.json.audit.jsonl" in ignore
