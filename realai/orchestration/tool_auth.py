"""Auth gate for POST /v1/tools/execute.

Off by default on a loopback dev box. Turn on with REALAI_TOOLS_AUTH=1.
The gate is FORCED on (fail closed) when REALAI_ENV=production or when the
server binds a non-loopback host; in that case the orchestrator refuses to
start unless REALAI_TOOLS_TOKEN is set (see ``startup_check``).

When on:

* ``Authorization: Bearer <token>`` must match REALAI_TOOLS_TOKEN
  (compared with hmac.compare_digest). Missing or wrong -> 401.
* Gate on but REALAI_TOOLS_TOKEN unset/empty -> 503 (fail closed).
* Tool name must be on the allowlist -> otherwise 403. Default allowlist is
  READ_ONLY_TOOLS only. Extra tools come only from REALAI_TOOLS_ALLOW
  (comma separated), which is added to the read-only set.
* Per-client fixed-window rate limit (REALAI_TOOLS_RATE calls per
  REALAI_TOOLS_RATE_WINDOW seconds; default 60/60) -> 429. Calls that have
  not authenticated use a separate pre-auth bucket. The limiter map is capped
  (MAX_CLIENTS) with oldest-first eviction.
* One audit line per call: sanitized ability name, result, sanitized client.
  Never the token, never payloads.

Response bodies for 401/403/503 are generic. The token is never logged or returned.
"""
from __future__ import annotations

import hmac
import ipaddress
import logging
import os
import re
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Mapping, Optional, Tuple

audit_log = logging.getLogger("realai.tools_audit")

_TRUTHY = {"1", "true", "yes", "on"}
_SAFE_RE = re.compile(r"[^A-Za-z0-9._:-]")
MAX_CLIENTS = 4096

# Core tools that only read state. This is the whole default allowlist.
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

_bind_host: Optional[str] = None


def set_bind_host(host: Optional[str]) -> None:
    """Record the host the orchestrator binds (called from main())."""
    global _bind_host
    _bind_host = None if host is None else str(host)


def is_loopback(host: Optional[str]) -> bool:
    if host is None:
        return True
    h = str(host).strip().strip("[]").lower()
    if h in ("localhost", ""):
        return h == "localhost"
    try:
        return ipaddress.ip_address(h).is_loopback
    except ValueError:
        return False


def forced(env: Optional[Mapping[str, str]] = None, bind_host: Optional[str] = None) -> bool:
    env = os.environ if env is None else env
    if str(env.get("REALAI_ENV", "")).strip().lower() == "production":
        return True
    host = _bind_host if bind_host is None else bind_host
    return not is_loopback(host)


def enabled(env: Optional[Mapping[str, str]] = None, bind_host: Optional[str] = None) -> bool:
    env = os.environ if env is None else env
    if forced(env, bind_host):
        return True
    return str(env.get("REALAI_TOOLS_AUTH", "")).strip().lower() in _TRUTHY


def startup_check(bind_host: Optional[str], env: Optional[Mapping[str, str]] = None) -> None:
    """Refuse to start when the gate is forced on and no token is configured."""
    env = os.environ if env is None else env
    if forced(env, bind_host) and not str(env.get("REALAI_TOOLS_TOKEN", "") or ""):
        raise SystemExit(
            "refusing to start: tools auth is forced on (REALAI_ENV=production or non-loopback bind) "
            "but REALAI_TOOLS_TOKEN is not set"
        )


def default_allowlist() -> FrozenSet[str]:
    return frozenset(READ_ONLY_TOOLS)


def allowlist(env: Optional[Mapping[str, str]] = None) -> FrozenSet[str]:
    env = os.environ if env is None else env
    raw = env.get("REALAI_TOOLS_ALLOW")
    extra = frozenset()
    if raw is not None and raw.strip():
        extra = frozenset(x.strip() for x in raw.split(",") if x.strip())
    return default_allowlist() | extra


def safe(value: Any, limit: int = 120) -> str:
    """Strip to [A-Za-z0-9._:-] and cap length (audit-log injection guard)."""
    return _SAFE_RE.sub("", str(value))[:limit]


@dataclass
class RateLimiter:
    limit: int = 60
    window: float = 60.0
    max_keys: int = MAX_CLIENTS
    _hits: "OrderedDict[str, Tuple[float, int]]" = field(default_factory=OrderedDict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def allow(self, client: str, now: Optional[float] = None) -> bool:
        now = time.monotonic() if now is None else now
        with self._lock:
            start, n = self._hits.get(client, (now, 0))
            if now - start >= self.window:
                start, n = now, 0
            ok = n < self.limit
            self._hits[client] = (start, n + 1 if ok else n)
            self._hits.move_to_end(client)
            if len(self._hits) > self.max_keys:
                # Drop expired windows first, then oldest entries.
                for k in [k for k, (s, _) in self._hits.items() if now - s >= self.window]:
                    if len(self._hits) <= self.max_keys:
                        break
                    del self._hits[k]
                while len(self._hits) > self.max_keys:
                    self._hits.popitem(last=False)
            return ok

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


def _audit(tool: Any, result: str, client: Any) -> None:
    # Only the sanitized ability name, the result and the sanitized client.
    audit_log.info("tools_execute ability=%s result=%s client=%s", safe(tool), result, safe(client, 64))


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
    tool: Any,
    headers: Mapping[str, str],
    client: str,
    env: Optional[Mapping[str, str]] = None,
    bind_host: Optional[str] = None,
) -> Optional[Tuple[int, Dict[str, str]]]:
    """Return None when the call may proceed, else (status, json_body)."""
    env = os.environ if env is None else env
    if not enabled(env, bind_host):
        return None
    if not isinstance(tool, str) or not tool:
        _audit(tool, "400_bad_tool_name", client)
        return 400, {"error": "bad_request"}
    expected = str(env.get("REALAI_TOOLS_TOKEN", "") or "")
    if not expected:
        _audit(tool, "503_no_token_configured", client)
        return 503, {"error": "unavailable"}
    got = _bearer(headers)
    authed = got is not None and hmac.compare_digest(got.encode("utf-8"), expected.encode("utf-8"))
    bucket = ("auth:" if authed else "pre:") + str(client)
    if not limiter(env).allow(bucket):
        _audit(tool, "429_rate_limited", client)
        return 429, {"error": "rate_limited"}
    if not authed:
        _audit(tool, "401_unauthorized", client)
        return 401, {"error": "unauthorized"}
    if tool not in allowlist(env):
        _audit(tool, "403_not_allowlisted", client)
        return 403, {"error": "forbidden"}
    _audit(tool, "200_allowed", client)
    return None
