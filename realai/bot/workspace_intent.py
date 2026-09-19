"""Parse Console chat intents that switch the active Craft workspace."""

from __future__ import annotations

import re
import threading
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

# Session id → absolute workspace path (survives across turns in one Console thread).
_SESSION_WS: Dict[str, str] = {}
_SESSION_LOCK = threading.Lock()

_WORK_IN_RE = re.compile(
    r"(?is)\b(?:"
    r"work\s+in|use\s+workspace|switch\s+(?:workspace\s+)?to|set\s+workspace(?:\s+to)?|"
    r"open\s+(?:the\s+)?(?:repo|project|folder)|cd\s+to"
    r")\s+[\"']?(.+?)[\"']?(?=\s*(?:$|[.\n]|then\b|and\b|,|\s+and\s+))"
)

_WIN_PATH_RE = re.compile(
    r"(?i)(?:[a-zA-Z]:[\\/][^\s\"']+|\\\\[^\s\"']+)"
)
_POSIX_ABS_RE = re.compile(r"(?<![\w:])(/(?:[\w.-]+/)+[\w.-]+)")
_GIT_URL_RE = re.compile(
    r"(?i)\b((?:https?://|git@)[^\s\"']+|(?:github\.com|gitlab\.com)/[\w.-]+/[\w.-]+)"
)


def _clean_candidate(raw: str) -> str:
    s = (raw or "").strip().strip("\"'").rstrip(".,;:")
    # Drop trailing "and then ..." crumbs if the regex over-captured.
    s = re.split(r"(?i)\s+\b(?:then|and then)\b\s+", s, maxsplit=1)[0].strip()
    return s


def extract_workspace_target(text: str) -> Optional[str]:
    """Return a local path or git URL the user wants as workspace, or None."""
    t = (text or "").strip()
    if not t:
        return None

    m = _WORK_IN_RE.search(t)
    if m:
        cand = _clean_candidate(m.group(1))
        if cand and cand.lower() not in {"this", "here", "the repo", "the project"}:
            return cand

    # Bare absolute path after a soft cue
    low = t.lower()
    if any(k in low for k in ("work in", "workspace", "switch to", "cd ")):
        wm = _WIN_PATH_RE.search(t)
        if wm:
            return _clean_candidate(wm.group(0))
        pm = _POSIX_ABS_RE.search(t)
        if pm:
            return _clean_candidate(pm.group(1))
        gm = _GIT_URL_RE.search(t)
        if gm:
            return _clean_candidate(gm.group(1))
    return None


def looks_like_workspace_switch(text: str) -> bool:
    return extract_workspace_target(text) is not None


def is_git_source(source: str) -> bool:
    s = (source or "").strip()
    if not s:
        return False
    low = s.lower()
    if low.startswith("http://") or low.startswith("https://") or low.startswith("git@"):
        return True
    if "github.com/" in low or "gitlab.com/" in low:
        return True
    # Windows / existing folder → local
    p = Path(s)
    if p.exists():
        return False
    return bool(urlparse(s).scheme)


def resolve_local_workspace(source: str) -> Tuple[Optional[Path], Optional[str]]:
    """Resolve a local folder to an absolute path. Error string on failure."""
    raw = (source or "").strip().strip("\"'")
    if not raw:
        return None, "empty workspace path"
    if is_git_source(raw):
        return None, "git_url"  # caller should learn/clone first
    try:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            # Relative to current product workspace, not process cwd
            from realai.workspace import product_root

            p = product_root() / p
        p = p.resolve()
    except OSError as exc:
        return None, str(exc)
    if not p.exists():
        return None, f"path not found: {p}"
    if not p.is_dir():
        return None, f"not a directory: {p}"
    return p, None


def get_session_workspace(session_id: str) -> Optional[str]:
    sid = (session_id or "").strip()
    if not sid:
        return None
    with _SESSION_LOCK:
        return _SESSION_WS.get(sid)


def set_session_workspace(session_id: str, path: Optional[str]) -> Optional[str]:
    sid = (session_id or "").strip()
    if not sid:
        return None
    with _SESSION_LOCK:
        if not path:
            _SESSION_WS.pop(sid, None)
            return None
        _SESSION_WS[sid] = str(path)
        return _SESSION_WS[sid]


def clear_session_workspace(session_id: str) -> None:
    set_session_workspace(session_id, None)


def bind_session_workspace_for_request(session_id: Optional[str]) -> Optional[Path]:
    """Apply stored session workspace as the request ContextVar override."""
    from realai.workspace import set_request_workspace

    sid = (session_id or "").strip()
    if not sid:
        return set_request_workspace(None)
    stored = get_session_workspace(sid)
    if not stored:
        return set_request_workspace(None)
    return set_request_workspace(stored)
