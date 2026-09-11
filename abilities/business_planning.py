"""Business planning — local Hive specialist (no cloud API)."""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "business_planning",
    "name": "business_planning",
    "type": "ability",
    "status": "LIVE",
    "source": "local Hive chat",
    "dest": "abilities/business_planning.py",
    "capabilities": ["business", "planning", "strategy", "local_hive"],
    "secrets_policy": "none",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    brief = str(ctx.get("brief") or ctx.get("input") or input or ctx.get("prompt") or "").strip()
    if not brief:
        return {"ok": False, "error": "brief_required", "ability": "business_planning"}

    system = (
        "You are RealAI Business Planner on the local Hive. "
        "Produce a concrete, actionable mini business plan with: "
        "1) Problem 2) Solution 3) Customer 4) Offer 5) GTM 6) 30-day milestones 7) Risks. "
        "Be terse and practical. No cloud services assumed."
    )
    from realai.local_media import hive_chat

    out = hive_chat(brief, system=system, max_tokens=int(ctx.get("max_tokens") or 512))
    return {
        "ok": bool(out.get("ok")),
        "ability": "business_planning",
        "brief": brief,
        "plan": out.get("text") or "",
        "backend": "local_hive_chat",
        "local": True,
        "live_path": "POST /v1/tools/execute ability.business_planning → Hive :8001",
        "model": out.get("model"),
    }
