"""Inbound request guard for the RealAI Hive v3 orchestrator (:8001).

Stdlib only (loaded by file path from v3_orchestrator; no package side effects).  Defends the local Hive against DNS-rebinding, cross-site
request forgery from other browser tabs, oversize bodies and request floods,
and (optionally) requires an inbound token for privileged routes.

Environment knobs (all optional):

  REALAI_HIVE_GUARD=0            disable every check (escape hatch)
  REALAI_ALLOWED_HOSTS=a,b       extra Host header names (default loopback only)
  REALAI_ALLOWED_ORIGINS=o1,o2   extra browser Origins allowed to POST
  REALAI_MAX_BODY_BYTES=N        POST body cap (default 1 MiB)
  REALAI_MAX_AUDIO_BODY_BYTES=N  cap for /v1/audio/* (default 32 MiB)
  REALAI_RATE_LIMIT=N            POSTs per client IP per minute (OPT-IN; default 0 = off)
  REALAI_PRIV_RATE_LIMIT=N       privileged POSTs per IP per minute (OPT-IN; default 0 = off)
  REALAI_HIVE_TOKEN_MODE=1       require the inbound token on privileged routes
  REALAI_HIVE_TOKEN_FILE=path    token file (default ~/.realai/hive_token)

Token mode: the token is auto-generated (secrets.token_urlsafe) on first use,
written with owner-only permissions and NEVER logged or returned in a body.
Clients send it as ``X-RealAI-Token: <t>`` or ``Authorization: Bearer <t>``;
same-origin pages served by the Hive (console, fusion-ui, agents-ui,
voice-lab) receive it as an HttpOnly SameSite=Strict cookie.
"""

from __future__ import annotations

import hmac
import os
import secrets
import threading
import time
from collections import deque
from pathlib import Path
from typing import Deque, Dict, Iterable, List, Mapping, Optional, Tuple

TOKEN_HEADER = "X-RealAI-Token"
COOKIE_NAME = "realai_hive_token"

LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")
# Browser UIs that legitimately call the Hive cross-origin.
DEFAULT_UI_PORTS = (3000, 8787, 5173)

# Routes that can execute code / tools, mutate weights or run agents.
PRIVILEGED_EXACT = frozenset(
    {
        "/v1/tools/execute",
        "/v1/abilities/run",
        "/v1/craft",
        "/v1/hive",
        "/v1/agents/run",
        "/v1/agents/simulation",
        "/v1/multi-agent/run",
        "/v1/recovery/promote",
        "/v1/learn/promote",
        "/v1/learn/wire",
        "/v1/weights/scan",
    }
)
PRIVILEGED_PREFIXES = ("/v1/self-heal/",)

# Pages that get the token cookie (same-origin console surfaces).
COOKIE_PAGE_PREFIXES = ("/console", "/ui", "/fusion-ui", "/agents-ui", "/voice-lab")

_JSON_TYPES = ("application/json", "application/x-ndjson")


def _env_flag(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    try:
        return int(str(os.environ.get(name, "")).strip() or default)
    except ValueError:
        return default


def _csv(name: str) -> List[str]:
    return [p.strip() for p in (os.environ.get(name) or "").split(",") if p.strip()]


def is_privileged(path: str) -> bool:
    p = (path or "/").split("?", 1)[0].rstrip("/") or "/"
    return p in PRIVILEGED_EXACT or any(p.startswith(x) or p + "/" == x for x in PRIVILEGED_PREFIXES)


def split_host(value: str) -> str:
    """Return the lowercase host name from a Host header (port stripped)."""
    v = (value or "").strip().lower()
    if v.startswith("["):
        end = v.find("]")
        return v[1:end] if end > 0 else v
    if v.count(":") == 1:
        return v.split(":", 1)[0]
    return v


class _RateLimiter:
    def __init__(self) -> None:
        self._hits: Dict[Tuple[str, str], Deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, bucket: str, key: str, limit: int, window: float = 60.0) -> bool:
        if limit <= 0:
            return True
        now = time.monotonic()
        with self._lock:
            dq = self._hits.setdefault((bucket, key), deque())
            while dq and now - dq[0] > window:
                dq.popleft()
            if len(dq) >= limit:
                return False
            dq.append(now)
            if len(self._hits) > 4096:  # bound memory
                for k in [k for k, d in self._hits.items() if not d][:2048]:
                    self._hits.pop(k, None)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


_LIMITER = _RateLimiter()
_TOKEN_LOCK = threading.Lock()
_TOKEN_CACHE: Dict[str, str] = {}


def token_path() -> Path:
    raw = os.environ.get("REALAI_HIVE_TOKEN_FILE")
    return Path(raw).expanduser() if raw else Path.home() / ".realai" / "hive_token"


def load_or_create_token(path: Optional[Path] = None) -> str:
    """Read (or create, owner-only) the inbound token.  Never log the value."""
    p = Path(path) if path else token_path()
    key = str(p)
    with _TOKEN_LOCK:
        if key in _TOKEN_CACHE:
            return _TOKEN_CACHE[key]
        tok = ""
        try:
            if p.is_file():
                tok = p.read_text(encoding="utf-8").strip()
        except OSError:
            tok = ""
        if len(tok) < 16:
            tok = secrets.token_urlsafe(32)
            p.parent.mkdir(parents=True, exist_ok=True)
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            fd = os.open(str(p), flags, 0o600)
            try:
                os.write(fd, tok.encode("utf-8"))
            finally:
                os.close(fd)
            try:
                os.chmod(str(p), 0o600)
            except OSError:
                pass
            if os.name == "nt":  # best effort: strip inherited ACLs to the current user
                try:
                    import subprocess

                    user = os.environ.get("USERNAME") or ""
                    if user:
                        subprocess.run(
                            ["icacls", str(p), "/inheritance:r", "/grant:r", f"{user}:F"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            timeout=10,
                            check=False,
                        )
                except Exception:
                    pass
        _TOKEN_CACHE[key] = tok
        return tok


def _reset_for_tests() -> None:
    _LIMITER.reset()
    with _TOKEN_LOCK:
        _TOKEN_CACHE.clear()


class GuardConfig:
    def __init__(self, server_port: int = 8001, bind_host: str = "127.0.0.1") -> None:
        self.enabled = _env_flag("REALAI_HIVE_GUARD", True)
        self.server_port = int(server_port or 8001)
        hosts = set(LOOPBACK_HOSTS)
        bh = split_host(bind_host or "")
        if bh and bh not in ("0.0.0.0", "::", ""):
            hosts.add(bh)
        hosts.update(h.lower() for h in _csv("REALAI_ALLOWED_HOSTS"))
        self.allowed_hosts = frozenset(hosts)
        origins = set()
        ports = (self.server_port,) + tuple(p for p in DEFAULT_UI_PORTS if p != self.server_port)
        for scheme in ("http", "https"):
            for host in ("127.0.0.1", "localhost", "[::1]"):
                for port in ports:
                    origins.add(f"{scheme}://{host}:{port}")
        origins.update(o.rstrip("/").lower() for o in _csv("REALAI_ALLOWED_ORIGINS"))
        self.allowed_origins = frozenset(origins)
        self.max_body = _env_int("REALAI_MAX_BODY_BYTES", 1 << 20)
        self.max_audio_body = _env_int("REALAI_MAX_AUDIO_BODY_BYTES", 32 << 20)
        self.rate_limit = _env_int("REALAI_RATE_LIMIT", 0)
        self.priv_rate_limit = _env_int("REALAI_PRIV_RATE_LIMIT", 0)
        self.token_mode = _env_flag("REALAI_HIVE_TOKEN_MODE", False)

    def origin_allowed(self, origin: str) -> bool:
        o = (origin or "").strip().rstrip("/").lower()
        if not o:
            return True
        if o.startswith("vscode-webview://"):
            return True  # VS Code extension webview console
        return o in self.allowed_origins

    def body_cap(self, path: str) -> int:
        return self.max_audio_body if (path or "").startswith("/v1/audio/") else self.max_body


class Decision:
    __slots__ = ("ok", "status", "error", "detail")

    def __init__(self, ok: bool, status: int = 200, error: str = "", detail: str = "") -> None:
        self.ok, self.status, self.error, self.detail = ok, status, error, detail

    def body(self) -> Dict[str, str]:
        return {"error": self.error, "detail": self.detail, "guard": "realai-hive"}


OK = Decision(True)


def _cookie_token(cookie_header: str) -> str:
    for part in (cookie_header or "").split(";"):
        k, _, v = part.strip().partition("=")
        if k == COOKIE_NAME:
            return v.strip()
    return ""


def presented_token(headers: Mapping[str, str]) -> str:
    t = (headers.get(TOKEN_HEADER) or "").strip()
    if t:
        return t
    auth = (headers.get("Authorization") or "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return _cookie_token(headers.get("Cookie") or "")


def is_authorized(cfg: GuardConfig, headers: Mapping[str, str]) -> bool:
    """True when token mode is off, or the request carries the right token."""
    if not cfg.enabled or not cfg.token_mode:
        return True
    want = load_or_create_token()
    got = presented_token(headers)
    return bool(got) and hmac.compare_digest(got.encode("utf-8"), want.encode("utf-8"))


def check_request(
    cfg: GuardConfig,
    method: str,
    path: str,
    headers: Mapping[str, str],
    client_ip: str,
) -> Decision:
    """Checks that run before the body is read.  Cheap, no I/O."""
    if not cfg.enabled:
        return OK
    host = headers.get("Host")
    if host is not None and split_host(host) not in cfg.allowed_hosts:
        return Decision(False, 421, "host_not_allowed", "Host header is not a loopback/allowlisted name")
    m = (method or "").upper()
    if m != "POST":
        return OK
    origin = headers.get("Origin")
    if origin is not None and not cfg.origin_allowed(origin):
        return Decision(False, 403, "origin_not_allowed", "Origin is not on the Hive allowlist")
    try:
        n = int(headers.get("Content-Length") or 0)
    except ValueError:
        return Decision(False, 400, "bad_content_length", "")
    if n < 0:
        return Decision(False, 400, "bad_content_length", "")
    if (headers.get("Transfer-Encoding") or "").lower().strip() not in ("", "identity"):
        return Decision(False, 411, "length_required", "chunked bodies are not accepted")
    if n > cfg.body_cap(path):
        return Decision(False, 413, "body_too_large", f"limit {cfg.body_cap(path)} bytes")
    if n > 0:
        ctype = (headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        if ctype:
            if ctype not in _JSON_TYPES and not ctype.endswith("+json"):
                return Decision(False, 415, "json_only", "POST bodies must be application/json")
        elif origin is not None:
            # Browsers always label bodies; an unlabeled browser body is suspicious.
            return Decision(False, 415, "json_only", "POST bodies must be application/json")
    priv = is_privileged(path)
    ip = client_ip or "?"
    if not _LIMITER.allow("post", ip, cfg.rate_limit):
        return Decision(False, 429, "rate_limited", "too many POSTs; slow down")
    if priv and not _LIMITER.allow("priv", ip, cfg.priv_rate_limit):
        return Decision(False, 429, "rate_limited", "too many privileged POSTs; slow down")
    if priv and not is_authorized(cfg, headers):
        return Decision(
            False,
            401,
            "token_required",
            f"token mode is on; send {TOKEN_HEADER} (token file: ~/.realai/hive_token)",
        )
    return OK


def wants_cookie(cfg: GuardConfig, path: str) -> bool:
    if not (cfg.enabled and cfg.token_mode):
        return False
    p = (path or "").split("?", 1)[0]
    return any(p == x or p.startswith(x + "/") or p.startswith(x + ".") for x in COOKIE_PAGE_PREFIXES)


def cookie_header_value() -> str:
    return f"{COOKIE_NAME}={load_or_create_token()}; Path=/; HttpOnly; SameSite=Strict"


def allowed_origins_sorted(cfg: GuardConfig) -> Iterable[str]:
    return sorted(cfg.allowed_origins)
