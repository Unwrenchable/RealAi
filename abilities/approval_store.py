"""Thin wrap over ``realai.plugins.tools.approval_store`` (human approval gate)."""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "approval_store",
    "name": "approval_store",
    "type": "ability",
    "status": "CODE",
    "source": "realai.plugins.tools.approval_store",
    "dest": "abilities/approval_store.py",
    "capabilities": ["approval", "human_gate", "high_risk_actions"],
    "secrets_policy": "none — approval metadata only",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    from realai.plugins.tools import approval_store as store

    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or input or "list").lower().strip()

    if action in {"list", "pending", "status"}:
        items = store.list_requests() if hasattr(store, "list_requests") else store._load().get("items", [])
        return {"ok": True, "ability": "approval_store", "action": "list", "items": items}

    if action in {"create", "request"}:
        req_action = str(ctx.get("request_action") or ctx.get("target") or "unspecified")
        payload = dict(ctx.get("payload") or {})
        if input and "note" not in payload:
            payload["note"] = input
        if hasattr(store, "create_request"):
            item = store.create_request(req_action, payload)
        else:
            return {"ok": False, "error": "create_request missing"}
        return {"ok": True, "ability": "approval_store", "action": "create", "item": item}

    if action in {"approve", "reject"}:
        req_id = str(ctx.get("id") or ctx.get("request_id") or "")
        if not req_id:
            return {"ok": False, "error": "id required"}
        fn = getattr(store, action, None)
        if not callable(fn):
            return {"ok": False, "error": f"{action} missing"}
        return {"ok": True, "ability": "approval_store", "action": action, "result": fn(req_id)}

    exports = [n for n in dir(store) if not n.startswith("_")]
    return {"ok": True, "ability": "approval_store", "exports": exports[:40], "hint": "action=list|create|approve|reject"}
