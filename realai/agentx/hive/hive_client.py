"""Local RealAI Hive provider (:8001) for Overmind / playtest steps.

Talks to the v3 orchestrator's OpenAI-compatible ``/v1/chat/completions`` on loopback only.
Auth, in order: ``REALAI_HIVE_TOKEN`` env, the guard token file (``REALAI_HIVE_TOKEN_FILE`` or
``~/.realai/hive_token``, read-only, never created here), then ``REALAI_API_KEY``. The token is
never logged, returned or put in an error message. If the hive is down, callers fall back to
the local placeholder provider.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

LOOPBACK = {"127.0.0.1", "localhost", "::1"}
DEFAULT_BASE = "http://127.0.0.1:8001"


def hive_base() -> str:
    base = (os.environ.get("REALAI_HIVE_URL") or os.environ.get("REALAI_API_BASE") or DEFAULT_BASE).rstrip("/")
    host = urlparse(base).hostname or ""
    # Loopback only: never send the local token anywhere else.
    return base if host in LOOPBACK else DEFAULT_BASE


def _token_file() -> Path:
    raw = os.environ.get("REALAI_HIVE_TOKEN_FILE")
    return Path(raw).expanduser() if raw else Path.home() / ".realai" / "hive_token"


def local_token() -> str:
    tok = os.environ.get("REALAI_HIVE_TOKEN", "").strip()
    if tok:
        return tok
    try:
        p = _token_file()
        if p.is_file():
            tok = p.read_text(encoding="utf-8").strip()
            if tok:
                return tok
    except OSError:
        pass
    return os.environ.get("REALAI_API_KEY", "").strip()


def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json"}
    tok = local_token()
    if tok:
        h["X-RealAI-Token"] = tok
        h["Authorization"] = f"Bearer {tok}"
    return h


class HiveProvider:
    name = "realai-hive"

    def __init__(self, base: str | None = None, timeout: float | None = None):
        self.base = base or hive_base()
        self.timeout = timeout or float(os.environ.get("REALAI_HIVE_TIMEOUT", "120"))
        self._up: bool | None = None

    def available(self, refresh: bool = False) -> bool:
        if self._up is not None and not refresh:
            return self._up
        try:
            with urllib.request.urlopen(urllib.request.Request(self.base + "/health"), timeout=1.5) as r:
                self._up = 200 <= r.status < 300
        except Exception:
            self._up = False
        return self._up

    def complete(self, prompt: str, context: dict[str, Any] | None = None, dry_run: bool = False) -> dict[str, Any]:
        ctx = context or {}
        if dry_run:
            return {"provider": self.name, "content": f"[dry-run hive] {prompt[:200]}"}
        msgs = []
        if ctx.get("role"):
            msgs.append({"role": "system", "content": f"You are the {ctx['role']} agent in the RealAI hive."})
        msgs.append({"role": "user", "content": prompt})
        body: dict[str, Any] = {"messages": msgs, "stream": False}
        # Do not switch models: only pass one if the launcher already set it.
        if os.environ.get("REALAI_DEFAULT_MODEL"):
            body["model"] = os.environ["REALAI_DEFAULT_MODEL"]
        req = urllib.request.Request(self.base + "/v1/chat/completions", data=json.dumps(body).encode("utf-8"),
                                     headers=_headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                data = json.loads(r.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            return {"provider": self.name, "error": f"hive http {e.code}", "content": ""}
        except Exception as e:  # noqa: BLE001
            return {"provider": self.name, "error": f"hive unreachable: {type(e).__name__}", "content": ""}
        try:
            content = data["choices"][0]["message"]["content"]
        except Exception:
            content = data.get("content") or data.get("response") or ""
        return {"provider": self.name, "content": content, "model": data.get("model")}


def pick_provider(tags: list[str] | None = None, use_hive: bool | None = None, hive: HiveProvider | None = None):
    """Hive at :8001 when it answers /health, else the local placeholder provider."""
    from realai.agentx.providers.router import ProviderRouter

    if use_hive is None:
        use_hive = os.environ.get("REALAI_AGENTX_USE_HIVE", "1") != "0"
    if use_hive:
        hive = hive or HiveProvider()
        if hive.available():
            return hive, False
    return ProviderRouter().select_provider(list(tags or []), ["local"]), True
