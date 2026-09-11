"""Observability, auditing, and self-improvement loop status."""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "observability_self_improve",
    "name": "observability_self_improve",
    "type": "ability",
    "status": "LIVE",
    "source": "realai.self_heal + realai.self_improvement + realai.audit",
    "dest": "abilities/observability_self_improve.py",
    "capabilities": ["self_heal", "self_improve", "audit", "observability"],
    "secrets_policy": "none",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or input or "status").lower().strip()

    out: dict[str, Any] = {"ok": True, "ability": "observability_self_improve", "action": action}

    if action in {"heal", "self_heal", "self-heal"}:
        from realai.self_heal import status as heal_status

        out["self_heal"] = heal_status()
        return out

    if action in {"improve", "self_improve", "evaluate"}:
        try:
            from realai.v3_orchestrator import _self_improve_status

            out["self_improve"] = _self_improve_status()
        except Exception as e:
            out["self_improve"] = {"ok": False, "error": str(e)}
        return out

    if action in {"audit", "events"}:
        try:
            from realai.audit import AUDIT_LOGGER, OBSERVABILITY

            logger = AUDIT_LOGGER
            events = []
            if hasattr(logger, "list_events"):
                events = logger.list_events(limit=int(ctx.get("limit") or 20))
            elif hasattr(logger, "recent"):
                events = logger.recent(int(ctx.get("limit") or 20))
            out["audit"] = {
                "logger": type(logger).__name__,
                "events": events,
                "observability": type(OBSERVABILITY).__name__ if OBSERVABILITY is not None else None,
            }
        except Exception as e:
            out["audit"] = {"ok": False, "error": str(e)}
        return out

    # default aggregate status
    from realai.self_heal import status as heal_status

    out["self_heal"] = heal_status()
    try:
        from realai.v3_orchestrator import _self_improve_status

        out["self_improve"] = _self_improve_status()
    except Exception as e:
        out["self_improve"] = {"error": str(e)}
    try:
        from realai.audit import AUDIT_LOGGER

        out["audit"] = {"logger": type(AUDIT_LOGGER).__name__, "ok": True}
    except Exception as e:
        out["audit"] = {"ok": False, "error": str(e)}
    out["live_paths"] = [
        "GET /v1/self-heal/status",
        "GET /v1/self-improve/status",
        "POST /v1/self-improve/evaluate",
        "tools self_heal_*",
    ]
    return out
