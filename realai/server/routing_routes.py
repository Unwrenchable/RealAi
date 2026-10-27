"""Read-only routing introspection for :8000, recovered from git ref origin/RealAi-unified
(realai/server/router.py handle_provider_route / handle_tool_route, blob 4d823814b3; never merged).

OFF by default. Enabled only with REALAI_ROUTING_ROUTES=1, and consulted by ``dispatch_request`` after
every built-in route misses. Default :8000 behaviour (404 for these paths) is unchanged.

  POST /v1/providers/route  {"model": "<id>"?}               -> which provider/backend would serve the model
  POST /v1/tools/route      {"text": "...", "allowed_tools": [...]?, "provider": "...",
                             "chain": bool, "max_tools": int}   -> which tool would be picked (and an optional chain)

Nothing here executes a tool, calls a provider, or reads/writes files. Tool *execution*
(RealAi-unified handle_tool_execute) was deliberately not recovered: it reported success without running
anything, and exec belongs behind the approval gate.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

JSON = "application/json"
FLAG = "REALAI_ROUTING_ROUTES"


def enabled() -> bool:
    return os.environ.get(FLAG, "").strip().lower() in {"1", "true", "yes", "on"}


def _bad(msg: str) -> Tuple[int, Dict[str, Any], str]:
    return 400, {"error": {"message": msg}}, JSON


def handle_provider_route(payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any], str]:
    from .config import get_model_config, load_settings
    from .providers import provider_for_model

    model_name = payload.get("model") or load_settings().default_chat_model
    if not isinstance(model_name, str) or not model_name.strip():
        return _bad("model is required.")
    try:
        model_cfg = get_model_config(model_name)
        provider = provider_for_model(model_name)
    except ValueError:
        # Generic text (no exception internals in responses, CodeQL py/stack-trace-exposure).
        return 404, {"error": {"message": "Unknown model"}}, JSON
    health = provider.get("health") or {}
    return 200, {
        "model": model_name,
        "routing": {
            "provider": provider.get("id"),
            "backend": model_cfg.get("backend", "unknown"),
            "type": provider.get("type", "api"),
            "health": health,
            "capabilities": model_cfg.get("capabilities", []),
            "selected": bool(provider.get("enabled", False))
            and (health.get("status") if isinstance(health, dict) else None) in {"ready", "disabled"},
        },
    }, JSON


def handle_tool_route(payload: Dict[str, Any]) -> Tuple[int, Dict[str, Any], str]:
    from realai.plugins.tool_router import route

    from .tools_runtime import TOOLS

    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        return _bad("text is required.")
    allowed = payload.get("allowed_tools")
    if not isinstance(allowed, list) or not allowed:
        allowed = [t["name"] for t in TOOLS.list_tools() if isinstance(t, dict) and t.get("name")]
    allowed = [a for a in allowed if isinstance(a, str)]
    provider = payload.get("provider") if isinstance(payload.get("provider"), str) else "local"

    ranked = route(text, allowed, provider)
    # RealAi-unified fell back to the first allowed tool when nothing matched.
    selected: Optional[str] = ranked.get("selected") or (allowed[0] if allowed else None)
    manifest = None
    if selected:
        try:
            manifest = TOOLS.get(selected).to_dict()
        except (ValueError, AttributeError):
            manifest = None

    chain = []
    if payload.get("chain"):
        if "file_read" in allowed and "web_search" in allowed:
            chain = [
                {"name": "file_read", "reason": "local context first"},
                {"name": "web_search", "reason": "follow-up web lookup"},
            ]
        try:
            max_tools = int(payload.get("max_tools") or len(chain))
        except (TypeError, ValueError):
            max_tools = len(chain)
        chain = chain[: max(0, max_tools)]

    return 200, {
        "ok": True,
        "text": text,
        "selected": selected,
        "candidates": ranked.get("candidates", []),
        "provider": provider,
        "routing": {
            "selected": manifest or {"name": selected},
            "provider": provider,
            "allowed_tools": allowed,
            "reason": "plugin-based intent match" if ranked.get("selected") else "fallback: first allowed tool",
            "chain": chain,
            "executes": False,
        },
    }, JSON


def dispatch(method: str, path: str, payload: Any = None) -> Optional[Tuple[int, Dict[str, Any], str]]:
    if not enabled() or method != "POST":
        return None
    body = payload if isinstance(payload, dict) else {}
    if path == "/v1/providers/route":
        return handle_provider_route(body)
    if path == "/v1/tools/route":
        return handle_tool_route(body)
    return None
