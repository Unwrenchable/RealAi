"""Synthetic organs ability — thin wrap over ``modules.organs`` (already extracted).

No second copy of organ modules. Live Craft/Hive path already uses ``organs_task``.
"""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "organs_hive",
    "name": "organs_hive",
    "type": "ability",
    "status": "LIVE",
    "source": "modules.organs.request_path",
    "dest": "abilities/organs_hive.py",
    "capabilities": ["organ_pipeline", "orchestrate_with_organs", "cognitive_stack"],
    "secrets_policy": "none",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Run organ pipeline / orchestrate_with_organs on a goal string."""
    from modules.organs.request_path import orchestrate_with_organs, run_organ_pipeline

    ctx = dict(context or {})
    ctx.update(kwargs)
    goal = str(ctx.get("goal") or input or "").strip()
    if not goal:
        return {"ok": False, "error": "goal_required", "ability": "organs_hive"}
    organ_ids = ctx.get("organ_ids") or ctx.get("organs")
    if isinstance(organ_ids, str):
        organ_ids = [x.strip() for x in organ_ids.split(",") if x.strip()]
    payload = ctx.get("payload") if isinstance(ctx.get("payload"), dict) else {}
    if organ_ids:
        results = run_organ_pipeline(organ_ids, goal=goal, payload=payload)
        return {
            "ok": True,
            "ability": "organs_hive",
            "source": ABILITY["source"],
            "mode": "pipeline",
            "result": results,
        }
    out = orchestrate_with_organs(goal, agent_roles=ctx.get("agent_roles"))
    return {
        "ok": True,
        "ability": "organs_hive",
        "source": ABILITY["source"],
        "mode": "orchestrate",
        "result": out,
    }
