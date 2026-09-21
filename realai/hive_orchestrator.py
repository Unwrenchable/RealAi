"""Ability: unified hive orchestrator router + specialist cycle.

Imports live gold only. Product-root ``core.orchestration`` is a compat shim
kept for older callers; new code uses ``realai.orchestration.hive_router``.
"""
from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "hive_orchestrator",
    "name": "hive_orchestrator",
    "type": "ability",
    "status": "LIVE",
    "source": "realai.orchestration.hive_router",
    "dest": "abilities/hive_orchestrator.py",
    "capabilities": ["routing", "nested_orchestrators", "planner_specialist_critic_executor"],
    "secrets_policy": "none",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    from realai.orchestration.hive_router import (
        list_nest_orchestrators,
        register_routes,
        run_cycle,
    )

    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or "cycle").lower()
    if action in {"routes", "register", "list"}:
        return {"ok": True, "ability": "hive_orchestrator", **register_routes()}
    if action in {"nest", "exportable"}:
        return {"ok": True, "ability": "hive_orchestrator", "nest": list_nest_orchestrators()}
    task = input or str(ctx.get("task") or "hive status")
    agent = str(ctx.get("agent") or "researcher")
    result = run_cycle(task, agent=agent, persist=bool(ctx.get("persist", True)))
    result["ability"] = "hive_orchestrator"
    return result
