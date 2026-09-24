"""Thin hive agent entrypoints used by .github/agents/*.json script_path."""
from __future__ import annotations

from typing import Any, Dict


def run_agent(agent_id: str, task: str = "", **kwargs: Any) -> Dict[str, Any]:
    """Delegate a hive agent turn through the unified hive orchestrator."""
    from core.orchestration.hive_router import route_model, run_cycle

    model = route_model(agent_id, task)
    result = run_cycle(task or f"{agent_id} status", agent=agent_id, persist=True)
    result["agent_id"] = agent_id
    result["preferred_model"] = model
    return result
