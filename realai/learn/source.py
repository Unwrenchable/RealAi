"""Resolve a git-learn source: local path, owner/repo, or HTTPS URL."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

_OWNER_REPO = re.compile(r"^[\w.-]+/[\w.-]+$")
_URL = re.compile(r"^(https?://|git@)", re.I)

# Shallow tips of every remote branch (depth 1 still implies --single-branch
# unless --no-single-branch is passed explicitly).
CLONE_DEPTH = 1


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


def git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    env.setdefault("GIT_ASKPASS", "")
    return env


def clone_argv(url: str, dest: Path, *, depth: int | None = CLONE_DEPTH) -> list[str]:
    """git clone flags: all remote branches, optional shallow tips."""
    cmd = ["git", "clone", "--no-single-branch"]
    if depth:
        cmd.extend(["--depth", str(int(depth))])
    cmd.extend([url, str(dest)])
    return cmd


def fetch_all_argv() -> list[str]:
    return ["fetch", "--all", "--tags"]


def git_capture(root: Path, *args: str, timeout: int = 20) -> str:
    try:
        r = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=git_env(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if r.returncode != 0:
        return ""
    return (r.stdout or "").strip()


def git_run_ok(root: Path, *args: str, timeout: int = 20) -> bool:
    try:
        r = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=git_env(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0


def git_bytes(root: Path, *args: str, timeout: int = 60) -> bytes:
    try:
        r = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            timeout=timeout,
            check=False,
            env=git_env(),
        )
    except (OSError, subprocess.TimeoutExpired):
        return b""
    if r.returncode != 0:
        return b""
    return r.stdout or b""


def _git(root: Path, *args: str, timeout: int = 20) -> str:
    return git_capture(root, *args, timeout=timeout)


def is_git_work_tree(root: Path) -> bool:
    return git_capture(root, "rev-parse", "--is-inside-work-tree") == "true"


def git_show_file(root: Path, ref: str, rel: str, *, limit: int = 4000) -> str:
    """Read a blob at ref:path without checking out (text sample)."""
    rel_n = (rel or "").replace("\\", "/").strip()
    if not rel_n or rel_n.startswith("/") or ".." in rel_n.split("/"):
        return ""
    ref_n = (ref or "").strip()
    if not ref_n or "\n" in ref_n or "\x00" in ref_n:
        return ""
    candidates = [ref_n]
    if not ref_n.startswith("refs/") and ref_n != "HEAD":
        candidates.extend(
            [
                f"refs/heads/{ref_n}",
                f"refs/remotes/origin/{ref_n}",
                f"origin/{ref_n}",
            ]
        )
    for candidate in candidates:
        text = git_capture(root, "show", f"{candidate}:{rel_n}", timeout=20)
        if text:
            return text[:limit]
    return ""


def _canonical_branch_name(refname: str) -> str | None:
    raw = (refname or "").strip()
    if not raw:
        return None
    if raw.endswith("/HEAD") or raw in {"HEAD", "refs/HEAD"}:
        return None
    if raw.startswith("refs/heads/"):
        name = raw[len("refs/heads/") :]
        return name or None
    if raw.startswith("refs/remotes/"):
        rest = raw[len("refs/remotes/") :]
        _remote, sep, branch = rest.partition("/")
        if not sep or branch in {"", "HEAD"}:
            return None
        return branch
    return None


def list_branch_refs(root: Path) -> list[tuple[str, str]]:
    """Unique (short_name, refname) for local heads then remotes. Skips HEAD."""
    raw = git_capture(
        root,
        "for-each-ref",
        "--format=%(refname)",
        "refs/heads",
        "refs/remotes",
        timeout=30,
    )
    by_name: dict[str, str] = {}
    for line in raw.splitlines():
        refname = line.strip()
        name = _canonical_branch_name(refname)
        if not name or name in by_name:
            continue
        by_name[name] = refname
    return [(name, by_name[name]) for name in by_name]


def current_branch_name(root: Path) -> str:
    b = git_capture(root, "rev-parse", "--abbrev-ref", "HEAD")
    if not b or b == "HEAD":
        return ""
    return b


def ordered_branch_refs(
    root: Path, *, max_branches: int
) -> tuple[list[tuple[str, str]], int, list[str]]:
    """Current branch first, then others. Returns (scan_list, omitted, all_names)."""
    pairs = list_branch_refs(root)
    all_names = [n for n, _ in pairs]
    cur = current_branch_name(root)
    if cur:
        pairs = [p for p in pairs if p[0] == cur] + [p for p in pairs if p[0] != cur]
    else:
        pairs = [("HEAD", "HEAD")] + pairs
        if "HEAD" not in all_names:
            all_names = ["HEAD", *all_names]
    limit = max(1, int(max_branches))
    omitted = max(0, len(pairs) - limit)
    return pairs[:limit], omitted, all_names


def git_info(root: Path) -> dict[str, Any]:
    if not (root / ".git").exists() and not (root / ".git").is_file():
        head = _git(root, "rev-parse", "HEAD")
        if not head:
            return {"head": "", "branch": "", "remote": "", "branches": []}
    names = [n for n, _ in list_branch_refs(root)]
    return {
        "head": _git(root, "rev-parse", "HEAD"),
        "branch": _git(root, "rev-parse", "--abbrev-ref", "HEAD"),
        "remote": _git(root, "config", "--get", "remote.origin.url"),
        "branches": names,
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


def ensure_all_remote_refspec(root: Path) -> None:
    """Old --single-branch caches only track one ref; expand to every head."""
    git_run_ok(root, "remote", "set-branches", "origin", "*", timeout=30)
    git_run_ok(
        root,
        "config",
        "remote.origin.fetch",
        "+refs/heads/*:refs/remotes/origin/*",
        timeout=20,
    )


def fetch_all_refs(root: Path) -> bool:
    """Fetch every remote branch + tags. Safe no-op when origin is missing."""
    if not is_git_work_tree(root):
        return False
    remotes = git_capture(root, "remote", timeout=10)
    if not remotes:
        return True
    ensure_all_remote_refspec(root)
    return git_run_ok(root, *fetch_all_argv(), timeout=180)


def resolve_source(
    source: str,
    *,
    cache_dir: Path,
    refresh: bool = False,
) -> dict[str, Any]:
    """Return a local tree to scan. Never deletes user data; cache only."""
    raw = (source or ".").strip() or "."
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {'"', "'"}:
        raw = raw[1:-1].strip() or "."
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
    if dest.exists() and not ((dest / ".git").exists() or (dest / ".git").is_file()):
        shutil.rmtree(dest, ignore_errors=True)

    cloned = False
    reused = dest.exists() and ((dest / ".git").exists() or (dest / ".git").is_file())
    if not dest.exists():
        try:
            r = subprocess.run(
                clone_argv(url, dest),
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
                env=git_env(),
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
    fetch_ok = fetch_all_refs(path)
    info = git_info(path)
    info["fetch_ok"] = fetch_ok
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
