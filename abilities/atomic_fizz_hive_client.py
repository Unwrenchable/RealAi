"""Atomic Fizz hive HTTP client ability.

LIVE wire-up to the RealAI gateway (:8001) via the promoted plugin client paths.
Does not vendor Atomic Fizz into the hive. Does not touch rackup_coach.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ABILITY = {
    "id": "atomic_fizz_hive_client",
    "name": "atomic_fizz_hive_client",
    "type": "ability",
    "status": "LIVE",
    "source": "realai/plugins/atomic_fizz_realai/realai-client.js",
    "dest": "abilities/atomic_fizz_hive_client.py",
    "capabilities": ["hive_http_client", "health", "chat_completions", "afc_bridge"],
    "secrets_policy": "none required - REALAI_API_KEY defaults to realai on local hive",
}

_ROOT = Path(__file__).resolve().parents[1]
_PLUGIN = _ROOT / "realai" / "plugins" / "atomic_fizz_realai"
_CJS_CLIENT = _PLUGIN / "realai-client.js"
_MULTI = _PLUGIN / "realai-client.multiprovider.js"
_ENGINES = _PLUGIN / "engines_src"


def _base() -> str:
    return (
        os.environ.get("REALAI_API_BASE")
        or os.environ.get("REALAI_PROVIDER_URL")
        or "http://127.0.0.1:8001"
    ).rstrip("/")


def _key() -> str:
    return os.environ.get("REALAI_API_KEY") or os.environ.get("OPENAI_API_KEY") or "realai"


def client_paths() -> dict[str, Any]:
    return {
        "ok": _CJS_CLIENT.is_file(),
        "realai_home": str(_ROOT),
        "plugin_dir": str(_PLUGIN),
        "cjs_client": str(_CJS_CLIENT),
        "cjs_bytes": _CJS_CLIENT.stat().st_size if _CJS_CLIENT.is_file() else 0,
        "multiprovider": str(_MULTI),
        "multiprovider_present": _MULTI.is_file(),
        "engines_src": str(_ENGINES),
        "engines_src_present": _ENGINES.is_dir(),
        "afc_env": {
            "REALAI_HOME": os.environ.get("REALAI_HOME") or str(_ROOT),
            "REALAI_API_BASE": _base(),
            "REALAI_HIVE_CLIENT": os.environ.get("REALAI_HIVE_CLIENT") or str(_CJS_CLIENT),
        },
        "note": (
            "AFC should set REALAI_HOME + REALAI_API_BASE; Node CJS can require REALAI_HIVE_CLIENT. "
            "ESM scripts under the vault keep scripts/realai/realai-client.js pointed at the same base."
        ),
    }


def health() -> dict[str, Any]:
    url = f"{_base()}/health"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "RealAI-ability-atomic_fizz_hive_client/1.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                body = json.loads(raw)
            except Exception:
                body = {"raw": raw[:500]}
            return {
                "ok": 200 <= getattr(resp, "status", 200) < 300,
                "status": getattr(resp, "status", 200),
                "url": url,
                "body": body,
            }
    except Exception as e:
        return {"ok": False, "url": url, "error": str(e)}


def chat(prompt: str, model: str | None = None) -> dict[str, Any]:
    prompt = (prompt or "").strip()
    if not prompt:
        return {"ok": False, "error": "prompt_required"}
    url = f"{_base()}/v1/chat/completions"
    payload = {
        "model": model or os.environ.get("REALAI_MODEL") or "realai",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_key()}",
            "User-Agent": "RealAI-ability-atomic_fizz_hive_client/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            body = json.loads(raw) if raw else {}
            content = ((body.get("choices") or [{}])[0].get("message") or {}).get("content")
            return {
                "ok": True,
                "status": getattr(resp, "status", 200),
                "url": url,
                "content": content,
                "body": body,
            }
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:800]
        return {"ok": False, "status": e.code, "url": url, "error": detail}
    except Exception as e:
        return {"ok": False, "url": url, "error": str(e)}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or input or "paths").strip().lower()
    if action in {"paths", "client", "info", ""}:
        return {
            "ok": True,
            "ability": "atomic_fizz_hive_client",
            "action": "paths",
            "result": client_paths(),
            "live_path": "POST /v1/tools/execute ability.atomic_fizz_hive_client",
        }
    if action in {"health", "ping"}:
        h = health()
        return {
            "ok": bool(h.get("ok")),
            "ability": "atomic_fizz_hive_client",
            "action": "health",
            "result": h,
            "paths": client_paths(),
        }
    if action in {"chat", "complete", "prompt"}:
        prompt = str(ctx.get("prompt") or ctx.get("message") or input or "").strip()
        if prompt.lower() in {"chat", "complete", "prompt"}:
            prompt = str(ctx.get("prompt") or ctx.get("message") or "").strip()
        out = chat(prompt, model=ctx.get("model"))
        return {
            "ok": bool(out.get("ok")),
            "ability": "atomic_fizz_hive_client",
            "action": "chat",
            "result": out,
        }
    return {
        "ok": False,
        "ability": "atomic_fizz_hive_client",
        "error": "unknown_action",
        "hint": "action=paths|health|chat",
    }
