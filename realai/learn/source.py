"""Resolve a git-learn source: local path, owner/repo, or HTTPS URL."""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

_OWNER_REPO = re.compile(r"^[\w.-]+/[\w.-]+$")
_URL = re.compile(r"^(https?://|git@)", re.I)


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (name or "").lower()).strip("_")
    return s or "repo"


def infer_slug(source: str, resolved: Path | None = None) -> str:
    raw = (source or "").strip().rstrip("/")
    if _OWNER_REPO.match(raw) and not Path(raw).exists():
        return slugify(raw.split("/", 1)[1].removesuffix(".git"))
    if _URL.match(raw) or raw.endswith(".git"):
        stem = Path(raw.split("?")[0]).name.removesuffix(".git")
        return slugify(stem)
    if resolved is not None:
        return slugify(resolved.name)
    p = Path(raw).expanduser()
    return slugify(p.name or "repo")


def _git(root: Path, *args: str, timeout: int = 20) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if r.returncode != 0:
        return ""
    return (r.stdout or "").strip()


def git_info(root: Path) -> dict[str, str]:
    if not (root / ".git").exists() and not (root / ".git").is_file():
        # still try — worktrees use .git files
        head = _git(root, "rev-parse", "HEAD")
        if not head:
            return {"head": "", "branch": "", "remote": ""}
    return {
        "head": _git(root, "rev-parse", "HEAD"),
        "branch": _git(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "remote": _git(root, "config", "--get", "remote.origin.url"),
    }


def _to_clone_url(raw: str) -> str | None:
    s = raw.strip()
    if not s:
        return None
    if s.startswith("git@") or s.startswith("ssh://"):
        return s
    if re.match(r"^https?://", s, re.I):
        return s
    if s.endswith(".git") and "/" in s:
        return s
    if _OWNER_REPO.match(s):
        return f"https://github.com/{s}.git"
    return None


def resolve_source(
    source: str,
    *,
    cache_dir: Path,
    refresh: bool = False,
) -> dict[str, Any]:
    """Return a local tree to scan. Never deletes user data; cache only."""
    raw = (source or ".").strip() or "."
    expanded = Path(raw).expanduser()
    if expanded.exists():
        path = expanded.resolve()
        slug = infer_slug(raw, path)
        info = git_info(path)
        return {
            "ok": True,
            "kind": "local",
            "input": raw,
            "path": path,
            "slug": slug,
            "url": info.get("remote") or None,
            "cloned": False,
            "reused_cache": False,
            "git": info,
        }

    url = _to_clone_url(raw)
    if not url:
        return {
            "ok": False,
            "error": f"source_not_found:{raw}",
            "hint": "Pass a local path, owner/repo, or HTTPS git URL.",
            "input": raw,
            "kind": "missing",
        }

    slug = infer_slug(raw)
    dest = cache_dir / slug
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and refresh:
        shutil.rmtree(dest, ignore_errors=True)

    cloned = False
    reused = dest.exists() and ((dest / ".git").exists() or dest.is_dir())
    if not dest.exists():
        try:
            r = subprocess.run(
                ["git", "clone", "--depth", "1", "--single-branch", url, str(dest)],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            return {
                "ok": False,
                "error": f"clone_failed:{e}",
                "input": raw,
                "url": url,
                "kind": "remote",
            }
        if r.returncode != 0:
            err = (r.stderr or r.stdout or "clone_failed").strip().splitlines()[-1:] or ["clone_failed"]
            return {
                "ok": False,
                "error": err[0][:400],
                "input": raw,
                "url": url,
                "kind": "remote",
            }
        cloned = True
        reused = False

    path = dest.resolve()
    info = git_info(path)
    return {
        "ok": True,
        "kind": "remote",
        "input": raw,
        "path": path,
        "slug": slug,
        "url": url,
        "cloned": cloned,
        "reused_cache": reused and not cloned,
        "git": info,
    }
