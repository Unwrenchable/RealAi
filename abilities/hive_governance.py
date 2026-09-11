"""Hive governance — local agent roster, access profiles, and coverage steward."""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "hive_governance",
    "name": "hive_governance",
    "type": "ability",
    "status": "LIVE",
    "source": "local Hive agents + ability coverage",
    "dest": "abilities/hive_governance.py",
    "capabilities": ["governance", "enterprise", "agents", "local_hive"],
    "secrets_policy": "none",
    "aliases": ["hominis_enterprise"],
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or input or "status").strip().lower() or "status"

    agents: list[dict[str, Any]] = []
    agent_count = 0
    agents_err = None
    try:
        from pathlib import Path
        import json
        import os

        path = Path(
            os.environ.get("REALAI_AGENTS_PATH")
            or Path(__file__).resolve().parents[1] / "realai" / "agents" / "agentx" / "agents.json"
        )
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            agents = data if isinstance(data, list) else list(data.get("agents") or [])
            agent_count = len(agents)
    except Exception as e:
        agents_err = str(e)

    coverage: dict[str, Any] = {}
    try:
        from realai.ability_catalog import coverage_summary

        coverage = coverage_summary()
    except Exception as e:
        coverage = {"error": str(e)}

    profiles: list[Any] = []
    try:
        from realai.agent_activity import load_profiles

        profiles = load_profiles()
    except Exception:
        profiles = []

    if action in {"plan", "brief", "advise"}:
        from realai.local_media import hive_chat

        topic = str(ctx.get("topic") or ctx.get("prompt") or "local RealAI Hive governance")
        system = (
            "You are RealAI Hive Governance steward on the local Hive. "
            "Advise on agent governance, access profiles (safe/balanced/power), "
            "and local-only operations. No external APIs."
        )
        out = hive_chat(
            f"Agents={agent_count}. Coverage={coverage.get('weighted_pct')}. Topic: {topic}",
            system=system,
            max_tokens=400,
        )
        return {
            "ok": True,
            "ability": "hive_governance",
            "action": action,
            "advice": out.get("text") or "",
            "agent_count": agent_count,
            "coverage": coverage,
            "local": True,
            "live_path": "POST /v1/tools/execute ability.hive_governance",
        }

    sample = [
        {
            "id": a.get("id"),
            "role": a.get("role"),
            "risk": a.get("risk_level"),
            "profile": a.get("preferred_profile"),
        }
        for a in agents[:12]
    ]
    return {
        "ok": True,
        "ability": "hive_governance",
        "action": "status",
        "agent_count": agent_count,
        "agents_sample": sample,
        "profiles": profiles,
        "coverage": coverage,
        "governance": {
            "mode": "local_hive",
            "external_api_required": False,
            "access_profiles": [p.get("name") for p in profiles if isinstance(p, dict)],
        },
        "agents_error": agents_err,
        "local": True,
        "live_path": "POST /v1/tools/execute ability.hive_governance + GET /v1/agents",
        "formerly": "hominis_enterprise",
    }
