"""tools/repo_mirror: D:\\ARCHIVE only, allowlist, sparse exclusions, SHA256 manifest, types-only secrets report."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess

import pytest

def _load():
    """Load by path: some suites put realai/ first on sys.path, where realai/tools.py shadows the top-level tools package."""
    import importlib.util
    from pathlib import Path

    p = Path(__file__).resolve().parents[2] / "tools" / "repo_mirror.py"
    spec = importlib.util.spec_from_file_location("repo_mirror_under_test", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


M = _load()

FAKE_TOKEN = "ghp_" + "Z9" * 18  # runtime-built github_token look-alike (not a credential)

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="git not installed")


def _git(*a, cwd=None):
    subprocess.run(["git", *a], cwd=cwd, check=True, capture_output=True, text=True)


def _source(tmp_path, name):
    src = tmp_path / "src" / name
    files = {"README.md": "# Rack em up\n\nLeague app.\n", "src/rating.ts": "// glicko\nexport const k = 1;\n",
             "src/config.ts": f"const t = '{FAKE_TOKEN}';\n", ".env": f"API_KEY={FAKE_TOKEN}\n", ".env.example": "API_KEY=\n",
             "node_modules/x/index.js": "vendored\n", "logo.png": "\x89PNG fake\n", "CREDENTIAL_MANAGEMENT.md": "how to store creds\n",
             "docs/.npmrc": "//registry/:_authToken=abc\n", "big.txt": "x" * (M.MAX_MIRROR_FILE + 10)}
    for rel, text in files.items():
        p = src / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    _git("init", "-q", "-b", "main", cwd=src)
    _git("-c", "user.name=t", "-c", "user.email=t@e", "add", "-A", cwd=src)
    _git("-c", "user.name=t", "-c", "user.email=t@e", "commit", "-q", "-m", "init", cwd=src)
    _git("config", "uploadpack.allowfilter", "true", cwd=src)
    return src


def test_out_must_be_under_archive(capsys):
    assert M.under_archive(r"D:\ARCHIVE\repo-mirror") and M.under_archive(r"d:\archive\x\y")
    for bad in (r"C:\RealAI-clean\mirror", r"D:\ARCHIVE2\x", r"D:\ARCHIVE\..\Windows", r"C:\temp\m", "relative\\dir", r"E:\ARCHIVE"):
        assert not M.under_archive(bad), bad
    assert M.main(["--out", r"C:\RealAI-clean\mirror", "--dry-run"]) == 2
    assert "refused" in capsys.readouterr().out


def test_allowlist_refuses_excluded_and_unknown(capsys):
    for r in ("LustLink", "reverse-phone-search", "Productivitybot", "Domain-bot", "Token-scalper", "atomicfizzcaps", "nope"):
        assert M.main(["--repos", r, "--dry-run"]) == 2, r
    defaults = M.default_repos()
    assert "Token-scalper" not in defaults and "LustLink" not in defaults and "ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS-main" in defaults


def test_dry_run_plans_without_writes(tmp_path, capsys):
    assert M.main(["--dry-run", "--repos", "Rack_em_up"]) == 0
    p = json.loads(capsys.readouterr().out)
    cmd = p["steps"][0]["commands"][0]
    assert {"--depth", "--filter=blob:none", "--sparse", "--no-checkout"} <= set(cmd) and "core.symlinks=false" in cmd
    assert p["steps"][0]["url"] == "https://github.com/Unwrenchable/Rack_em_up.git"
    assert "!**/.env" in p["sparse_patterns"] and "!**/node_modules/" in p["sparse_patterns"]


def test_mirror_end_to_end(tmp_path, monkeypatch):
    src = _source(tmp_path, "Rack_em_up")
    archive = tmp_path / "ARCHIVE"
    out = archive / "repo-mirror"
    tmpl = "file://" + str(tmp_path / "src") + "/{repo}"
    assert M.main(["--out", str(out), "--repos", "Rack_em_up", "--url-template", tmpl], archive_root=str(archive)) == 0
    dst = out / "Rack_em_up"
    on_disk = {p.relative_to(dst).as_posix() for p in dst.rglob("*") if p.is_file() and ".git" not in p.relative_to(dst).parts}
    assert {"README.md", "src/rating.ts", "src/config.ts", ".env.example", "big.txt"} <= on_disk
    for never in (".env", "node_modules/x/index.js", "logo.png", "CREDENTIAL_MANAGEMENT.md", "docs/.npmrc"):
        assert never not in on_disk, never
    man = json.loads((out / "repo_mirror_manifest.json").read_text())
    r = man["repos"]["Rack_em_up"]
    assert len(r["commit"]) == 40 and r["files"]["README.md"]["sha256"] == hashlib.sha256((src / "README.md").read_bytes()).hexdigest()
    assert "src/config.ts" in r["blocked"] and "big.txt" in r["blocked"] and "README.md" not in r["blocked"]
    rep_p = next(out.glob("secrets-report-*.json"))
    rep = json.loads(rep_p.read_text())
    assert {"path": "src/config.ts", "types": ["assigned_secret", "github_token"]} in rep["repos"]["Rack_em_up"] or \
        any(f["path"] == "src/config.ts" and "github_token" in f["types"] for f in rep["repos"]["Rack_em_up"])
    for p in out.glob("*.json"):
        assert FAKE_TOKEN not in p.read_text()
    assert "ok Rack_em_up" in (out / "ACTIONS.log").read_text()

    # repo_search over the fresh mirror: flagged file refused, clean file readable
    from realai import hive_tools as H

    monkeypatch.setenv("REALAI_REPO_MIRROR", str(out))
    assert H.execute("repo_search", {"action": "read", "repo": "Rack_em_up", "path": "src/config.ts"})["ok"] is False
    assert H.execute("repo_search", {"action": "grep", "repo": "Rack_em_up", "query": "glicko"})["hits"][0]["path"] == "src/rating.ts"

    # second run never overwrites; manifest is backed up first
    before = (dst / "README.md").stat().st_mtime_ns
    assert M.main(["--out", str(out), "--repos", "Rack_em_up", "--url-template", tmpl], archive_root=str(archive)) == 0
    assert (dst / "README.md").stat().st_mtime_ns == before
    assert list(out.glob("repo_mirror_manifest.json.bak-*"))
    assert "skip Rack_em_up: exists" in (out / "ACTIONS.log").read_text()


def test_mirror_refuses_outside_archive(tmp_path):
    with pytest.raises(SystemExit):
        M.mirror(["Rack_em_up"], str(tmp_path / "elsewhere"), archive_root=str(tmp_path / "ARCHIVE"))
    assert not (tmp_path / "elsewhere").exists()
