"""Optional auth gate for POST /v1/tools/execute.

Off by default. Turn on with REALAI_TOOLS_AUTH=1. When on:

* ``Authorization: Bearer <token>`` must match REALAI_TOOLS_TOKEN
  (compared with hmac.compare_digest). Missing or wrong -> 401.
* Flag on but REALAI_TOOLS_TOKEN unset/empty -> 503 (fail closed).
* Tool name must be on the allowlist -> otherwise 403. Default allowlist is
  the read-only core tools plus every PARTIAL ability in the catalog.
  REALAI_TOOLS_ALLOW (comma separated) replaces the default.
* Simple per-client fixed-window rate limit
  (REALAI_TOOLS_RATE, calls per REALAI_TOOLS_RATE_WINDOW seconds; default 60/60) -> 429.
* One audit line per call: ability, result, client. Never the token, never payloads.

The token is never logged or returned.
"""
from __future__ import annotations

import hmac
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, Mapping, Optional, Tuple

audit_log = logging.getLogger("realai.tools_audit")

_TRUTHY = {"1", "true", "yes", "on"}

# Core tools that only read state.
READ_ONLY_TOOLS: FrozenSet[str] = frozenset(
    {
        "list_agents",
        "agent_tools_assess",
        "ability.pr_triage",
        "ability.vuln_triage",
        "ability.ci_failure_classify",
        "ability.coach",
        "rackup_invoke",
    }
)


def enabled(env: Optional[Mapping[str, str]] = None) -> bool:
    env = os.environ if env is None else env
    return str(env.get("REALAI_TOOLS_AUTH", "")).strip().lower() in _TRUTHY


def _partial_abilities() -> Iterable[str]:
    try:
        from realai.ability_catalog import RUNDOWN_ABILITIES
    except Exception:
        return ()
    out = []
    for a in RUNDOWN_ABILITIES:
        if str(a.get("status", "")).upper() == "PARTIAL" and a.get("id"):
            out.append("ability." + str(a["id"]))
    return out


def default_allowlist() -> FrozenSet[str]:
    return frozenset(READ_ONLY_TOOLS) | frozenset(_partial_abilities())


def allowlist(env: Optional[Mapping[str, str]] = None) -> FrozenSet[str]:
    env = os.environ if env is None else env
    raw = env.get("REALAI_TOOLS_ALLOW")
    if raw is not None and raw.strip():
        return frozenset(x.strip() for x in raw.split(",") if x.strip())
    return default_allowlist()


@dataclass
class RateLimiter:
    limit: int = 60
    window: float = 60.0
    _hits: Dict[str, Tuple[float, int]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def allow(self, client: str, now: Optional[float] = None) -> bool:
        now = time.monotonic() if now is None else now
        with self._lock:
            start, n = self._hits.get(client, (now, 0))
            if now - start >= self.window:
                start, n = now, 0
            if n >= self.limit:
                self._hits[client] = (start, n)
                return False
            self._hits[client] = (start, n + 1)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def _int_env(env: Mapping[str, str], key: str, default: int) -> int:
    try:
        return max(1, int(env.get(key, default)))
    except (TypeError, ValueError):
        return default


_limiter: Optional[RateLimiter] = None
_limiter_lock = threading.Lock()


def limiter(env: Optional[Mapping[str, str]] = None) -> RateLimiter:
    global _limiter
    env = os.environ if env is None else env
    with _limiter_lock:
        lim = _int_env(env, "REALAI_TOOLS_RATE", 60)
        win = _int_env(env, "REALAI_TOOLS_RATE_WINDOW", 60)
        if _limiter is None or _limiter.limit != lim or _limiter.window != win:
            _limiter = RateLimiter(limit=lim, window=float(win))
        return _limiter


def _audit(tool: str, result: str, client: str) -> None:
    # Only the ability name, the result and the client. No token, no payload.
    audit_log.info("tools_execute ability=%s result=%s client=%s", str(tool)[:120], result, client)


def _bearer(headers: Mapping[str, str]) -> Optional[str]:
    raw = None
    try:
        raw = headers.get("Authorization")
    except Exception:
        raw = None
    if not raw:
        return None
    parts = str(raw).strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def check(
    tool: str,
    headers: Mapping[str, str],
    client: str,
    env: Optional[Mapping[str, str]] = None,
) -> Optional[Tuple[int, Dict[str, str]]]:
    """Return None when the call may proceed, else (status, json_body)."""
    env = os.environ if env is None else env
    if not enabled(env):
        return None
    expected = str(env.get("REALAI_TOOLS_TOKEN", "") or "")
    if not expected:
        _audit(tool, "503_no_token_configured", client)
        return 503, {
            "error": "tools_auth_misconfigured",
            "message": "REALAI_TOOLS_AUTH is on but REALAI_TOOLS_TOKEN is not set; refusing all tool calls.",
        }
    if not limiter(env).allow(client):
        _audit(tool, "429_rate_limited", client)
        return 429, {"error": "rate_limited"}
    got = _bearer(headers)
    if got is None or not hmac.compare_digest(got.encode("utf-8"), expected.encode("utf-8")):
        _audit(tool, "401_unauthorized", client)
        return 401, {"error": "unauthorized", "message": "Authorization: Bearer <REALAI_TOOLS_TOKEN> required."}
    if str(tool) not in allowlist(env):
        _audit(tool, "403_not_allowlisted", client)
        return 403, {"error": "tool_not_allowed", "tool": str(tool)[:120]}
    _audit(tool, "200_allowed", client)
    return None
