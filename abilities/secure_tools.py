"""Ability surface for hardened SecureToolExecutor (hive)."""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "secure_tools",
    "name": "secure_tools",
    "type": "ability",
    "status": "LIVE",
    "source": "core.tools.hive_executor",
    "dest": "abilities/secure_tools.py",
    "capabilities": ["secure_execute", "approval_gate", "tool_routing"],
    "secrets_policy": "none",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    from core.tools.hive_executor import execute_secure, get_executor

    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or "execute").lower()
    if action in {"audit", "log"}:
        ex = get_executor()
        log = list(getattr(ex, "get_audit_log", lambda: [])() or [])
        return {"ok": True, "ability": "secure_tools", "audit": log[-50:]}

    tool = str(ctx.get("tool") or ctx.get("tool_name") or input or "").strip()
    if not tool:
        return {"ok": False, "error": "tool required", "hint": "tool=web_research|code_execution|..."}
    args = dict(ctx.get("arguments") or {})
    # allow flat kwargs as arguments
    for k, v in list(ctx.items()):
        if k not in {"action", "tool", "tool_name", "arguments", "approved", "approval_id", "force_approve"}:
            if k not in args:
                args[k] = v
    if input and "query" not in args and tool in {"web_research", "math_solver", "creative_writer"}:
        args.setdefault("query" if tool == "web_research" else "prompt" if tool == "creative_writer" else "problem", input)
    return execute_secure(
        tool,
        args,
        force_approve=bool(ctx.get("force_approve") or ctx.get("approved")),
    )
