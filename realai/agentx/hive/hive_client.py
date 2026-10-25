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
    # X-RealAI-Tools: off = the sanctioned IDE-client switch: the hive must not run its own
    # natural-mode tools / live_exec / model-write hooks on agent turns (our tools are read-only fs).
    h = {"Content-Type": "application/json", "X-RealAI-Tools": "off", "X-RealAI-Memory": "off"}
    tok = local_token()
    if tok:
        h["X-RealAI-Token"] = tok
        h["Authorization"] = f"Bearer {tok}"
    return h


NEUTRAL_TURN = "Reply now with exactly one JSON object as specified above, and nothing else."
NEUTRAL_TURN_ARRAY = "Output only the JSON array described above."
# Both fixed strings were checked against the hive natural-mode triggers (repo/write/patch/agent asks): no match.


def fold_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Put the whole agent transcript in the system message and end on a neutral user turn.

    The live hive runs "natural mode" on the LAST user message (Craft inspect, and for
    fix/patch/write asks it can apply model /write blocks to its own workspace). Tool results
    contain arbitrary file text, so they must never be the last user message. A fixed neutral
    turn ("Continue.") never triggers natural grounding, keeping agent turns read-only.
    """
    if len(messages) == 1 and messages[0].get("role") == "user" and len(messages[0].get("content", "")) < 4000:
        lines = [f"{m.get('role', 'user').upper()}: {m.get('content', '')}" for m in messages]
    else:
        lines = []
        for m in messages:
            role = m.get("role", "user")
            lines.append(m.get("content", "") if role == "system" else f"[{role}] {m.get('content', '')}")
    last = messages[-1].get("content", "") if messages else ""
    turn = NEUTRAL_TURN_ARRAY if "JSON array" in last else NEUTRAL_TURN
    return [{"role": "system", "content": "\n\n".join(lines)}, {"role": "user", "content": turn}]


def is_degenerate(text: str) -> bool:
    """True for broken model output such as '??????' (seen when the backend is unhealthy)."""
    t = "".join((text or "").split())
    if len(t) < 8:
        return False
    junk = sum(1 for ch in t if ch in "?\ufffd")
    return junk / len(t) > 0.6


class HiveProvider:
    name = "realai-hive"

    def __init__(self, base: str | None = None, timeout: float | None = None):
        self.base = base or hive_base()
        self.timeout = timeout or float(os.environ.get("REALAI_HIVE_TIMEOUT", "120"))
        self._up: bool | None = None
        self.last_error: str | None = None

    def available(self, refresh: bool = False) -> bool:
        if self._up is not None and not refresh:
            return self._up
        try:
            with urllib.request.urlopen(urllib.request.Request(self.base + "/health"), timeout=1.5) as r:
                self._up = 200 <= r.status < 300
        except Exception:
            self._up = False
        return self._up

    def chat(self, messages: list[dict[str, str]], max_tokens: int | None = None) -> str:
        """Raw multi-turn chat for the tool loop. Returns assistant text ('' on error)."""
        body: dict[str, Any] = {"messages": fold_messages(messages), "stream": False, "temperature": 0.2}
        if max_tokens:
            body["max_tokens"] = max_tokens
        if os.environ.get("REALAI_DEFAULT_MODEL"):
            body["model"] = os.environ["REALAI_DEFAULT_MODEL"]
        req = urllib.request.Request(self.base + "/v1/chat/completions", data=json.dumps(body).encode("utf-8"),
                                     headers=_headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                data = json.loads(r.read().decode("utf-8") or "{}")
            text = str(data["choices"][0]["message"]["content"] or "")
        except Exception:  # noqa: BLE001
            self.last_error = "hive_unreachable"
            return ""
        if is_degenerate(text):
            self.last_error = "degenerate_output"
            return ""
        self.last_error = None
        return text

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
        if is_degenerate(str(content)):
            return {"provider": self.name, "error": "degenerate model output", "content": ""}
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
