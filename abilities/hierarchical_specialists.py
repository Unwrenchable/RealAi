"""Thin ability over ``core.agents`` specialist registry + tool suite.

Promoted from hierarchical_agent_gold into live ``core/agents/{agents,tools}.py``.
"""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "hierarchical_specialists",
    "name": "hierarchical_specialists",
    "type": "ability",
    "status": "CODE",
    "source": "core.agents",
    "dest": "abilities/hierarchical_specialists.py",
    "capabilities": [
        "researcher",
        "coder",
        "creative",
        "executor",
        "critic",
        "specialist_tools",
    ],
    "secrets_policy": "none",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    from core.agents import get_agent, get_agent_registry, list_tools

    ctx = dict(context or {})
    ctx.update(kwargs)
    agent_type = str(ctx.get("agent") or ctx.get("agent_type") or "").lower().strip()
    action = str(ctx.get("action") or "invoke").lower().strip()

    if action in {"list", "registry", "tools"}:
        return {
            "ok": True,
            "ability": "hierarchical_specialists",
            "agents": sorted(get_agent_registry().keys()),
            "tools": list_tools(),
        }

    if not agent_type:
        # default: list when no agent specified
        if not input:
            return {
                "ok": True,
                "ability": "hierarchical_specialists",
                "agents": sorted(get_agent_registry().keys()),
                "tools": list_tools(),
                "hint": "pass agent=researcher|coder|creative|executor|critic",
            }
        agent_type = "researcher"

    agent = get_agent(agent_type)
    if agent is None:
        return {
            "ok": False,
            "error": f"unknown_agent:{agent_type}",
            "agents": sorted(get_agent_registry().keys()),
        }

    try:
        from langchain_core.messages import HumanMessage  # type: ignore

        messages = [HumanMessage(content=input or str(ctx.get("task") or "status"))]
    except Exception:
        messages = [input or str(ctx.get("task") or "status")]

    result = agent.invoke(messages)
    return {
        "ok": True,
        "ability": "hierarchical_specialists",
        "agent": agent_type,
        "expertise": getattr(agent, "expertise", None),
        "result": result,
    }
