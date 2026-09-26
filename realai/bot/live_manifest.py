"""Live manifest for capability and status turns.

Probes are real. A failed probe is one warning line. The card never
includes raw JSON, stack traces, or invented counts.

Learn stays GET-only. This module does not POST /v1/learn/queue.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple

_MANIFEST_RE = re.compile(
    r"(?i)("
    r"what can you (do|help(?: me)? with)|"
    r"what do you (do|offer)|"
    r"\bcapabilities?\b|"
    r"what('?s| is) your status|"
    r"\b(hive|system|stack) status\b|"
    r"\bstatus of (the )?(hive|stack|system|you)\b|"
    r"show me what you can do|"
    r"\bare you (up|live|running)\b|"
    r"what('?s| is) (up|live)\b"
    r")"
)

_OK_STATUS = {"ok", "healthy", "up"}
_FAIL_STATUS = {"degraded", "error", "fail", "failed", "down", "unhealthy"}

_COUNT_SPECS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("TTS", ("tts_count", "tts")),
    ("Vulkan", ("vulkan_count", "vulkan_models", "vulkan")),
    ("LoRA", ("lora_count", "lora_adapters", "lora")),
)


def is_manifest_turn(text: str) -> bool:
    """True for capability / status asks. A git-status act is not one."""
    raw = (text or "").strip()
    if not raw:
        return False
    ask = raw.split("\n\n", 1)[0]
    if re.search(r"(?i)\bgit\s+status\b", ask) and not _MANIFEST_RE.search(ask):
        return False
    return bool(_MANIFEST_RE.search(ask))


def unavailable_line(name: str) -> str:
    """One operator line for a failed probe. No payload."""
    label = " ".join(str(name or "probe").split()) or "probe"
    return f"⚠️ Unavailable: {label} — [Retry]"


def _as_count(value: Any) -> Optional[int]:
    """Integer count only. Bools, URLs, and status objects are not counts."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        token = value.strip()
        if token.isdigit():
            return int(token)
        return None
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        for key in ("count", "n", "adapters", "models", "voices"):
            if key in value:
                found = _as_count(value.get(key))
                if found is not None:
                    return found
        return None
    return None


def _optional_counts(payload: Dict[str, Any]) -> List[Tuple[str, int]]:
    """TTS / Vulkan / LoRA counts only when the health payload actually has them."""
    rows: List[Tuple[str, int]] = []
    details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
    for label, keys in _COUNT_SPECS:
        found: Optional[int] = None
        for source in (payload, details):
            if not isinstance(source, dict):
                continue
            for key in keys:
                if key not in source:
                    continue
                found = _as_count(source.get(key))
                if found is not None:
                    break
            if found is not None:
                break
        if found is not None:
            rows.append((label, found))
    return rows


def _health_ok(payload: Dict[str, Any]) -> bool:
    status = str(payload.get("status") or "").strip().lower()
    if status in _OK_STATUS:
        return True
    if status in _FAIL_STATUS:
        return False
    if not status:
        return True
    return False


def _last_ingest(payload: Dict[str, Any]) -> str:
    stamps: List[str] = []
    for key in ("last_ingest", "learned_at", "last_learned"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            stamps.append(val.strip())
    packets = payload.get("packets")
    if isinstance(packets, list):
        for row in packets:
            if not isinstance(row, dict):
                continue
            for key in ("learned_at", "ingested_at", "last_ingest"):
                val = row.get(key)
                if isinstance(val, str) and val.strip():
                    stamps.append(val.strip())
    if not stamps:
        return ""
    return max(stamps)


def _api_base() -> str:
    return (
        os.environ.get("REALAI_API_BASE")
        or os.environ.get("REALAI_PROVIDER_URL")
        or "http://127.0.0.1:8001"
    ).rstrip("/")


def _default_fetch(path: str, *, timeout: float = 1.2) -> Dict[str, Any]:
    """GET a JSON object. Failures stay flags. Bodies are not returned on error.

    404 is ``_missing`` (endpoint absent). Other failures are ``_error``.
    """
    url = _api_base() + (path if str(path).startswith("/") else "/" + str(path))
    try:
        req = urllib.request.Request(
            url,
            method="GET",
            headers={"User-Agent": "RealAI-manifest/1.0"},
        )
        with urllib.request.urlopen(req, timeout=float(timeout)) as resp:
            status = int(getattr(resp, "status", 200) or 200)
            raw = resp.read(16000).decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        if int(getattr(exc, "code", 0) or 0) == 404:
            return {"_missing": True}
        return {"_error": True}
    except Exception:
        return {"_error": True}
    if status == 404:
        return {"_missing": True}
    if not 200 <= status < 300:
        return {"_error": True}
    try:
        data = json.loads(raw) if raw else {}
    except Exception:
        return {"_error": True}
    if not isinstance(data, dict):
        return {"_error": True}
    return data


def _workspace_cwd() -> str:
    try:
        from realai.workspace import realai_workspace

        return str(realai_workspace())
    except Exception:
        return os.getcwd()


def _git_dirty() -> Dict[str, Any]:
    """Local git porcelain. There is no git-dirty HTTP route."""
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=_workspace_cwd(),
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=4,
        )
        return {"ok": True, "dirty": bool(out.strip())}
    except Exception:
        return {"ok": False}


def _learn_depth(payload: Dict[str, Any]) -> Optional[int]:
    depth = payload.get("count")
    if isinstance(depth, int) and not isinstance(depth, bool):
        return depth
    packets = payload.get("packets")
    if isinstance(packets, list):
        return len(packets)
    return None


def format_live_manifest(
    user_text: str = "",
    *,
    hat: str = "",
    fetch: Optional[Callable[..., Dict[str, Any]]] = None,
    git_probe: Optional[Callable[[], Dict[str, Any]]] = None,
) -> str:
    """Manifest card: inferred hat plus live probe lines.

    ``fetch(path)`` returns a dict. ``_missing`` omits an optional route
    (learn queue) instead of inventing a depth. ``_error`` becomes one
    warning line. Health is required, so a missing health route warns too.
    """
    from realai.bot.hat_routing import infer_hat, normalize_hat

    name = normalize_hat(hat) if str(hat or "").strip() else infer_hat(user_text)
    getter = fetch or _default_fetch
    lines: List[str] = [f"Mode: {name}", "Manifest:", f"- hat: {name}"]

    try:
        health = getter("/health")
    except Exception:
        health = {"_error": True}
    if not isinstance(health, dict) or health.get("_error") or health.get("_missing"):
        lines.append(unavailable_line("hive health"))
    else:
        lines.append(f"- hive health: {'ok' if _health_ok(health) else 'fail'}")
        for label, count in _optional_counts(health):
            lines.append(f"- {label}: {count}")

    try:
        learn = getter("/v1/learn/packets")
    except Exception:
        learn = {"_error": True}
    if isinstance(learn, dict) and learn.get("_missing"):
        pass
    elif not isinstance(learn, dict) or learn.get("_error"):
        lines.append(unavailable_line("learn queue"))
    else:
        depth = _learn_depth(learn)
        if depth is None:
            lines.append(unavailable_line("learn queue"))
        else:
            lines.append(f"- learn queue: {depth}")
            last = _last_ingest(learn)
            if last:
                lines.append(f"- last ingest: {last}")

    try:
        git = (git_probe or _git_dirty)()
    except Exception:
        git = {"ok": False}
    if not isinstance(git, dict) or not git.get("ok"):
        lines.append(unavailable_line("git"))
    else:
        lines.append(f"- git dirty: {'yes' if git.get('dirty') else 'no'}")

    return "\n".join(lines)
