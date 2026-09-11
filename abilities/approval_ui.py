"""Thin wrap over ``realai.plugins.tools.approval_ui`` (Flask + Slack approve UI)."""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "approval_ui",
    "name": "approval_ui",
    "type": "ability",
    "status": "CODE",
    "source": "realai.plugins.tools.approval_ui",
    "dest": "abilities/approval_ui.py",
    "capabilities": ["approval", "ui", "slack", "human_gate"],
    "secrets_policy": "optional SLACK_BOT_TOKEN / SLACK_SIGNING_SECRET / SLACK_APPROVAL_CHANNEL",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or input or "info").lower().strip()

    if action in {"info", "help", "status", ""}:
        return {
            "ok": True,
            "ability": "approval_ui",
            "impl": "realai.plugins.tools.approval_ui",
            "run": "python -m realai.plugins.tools.approval_ui",
            "default_url": "http://localhost:5001/",
            "actions": ["info", "start"],
            "note": "Requires Flask. Pairs with abilities/approval_store + abilities/notifier.",
        }

    if action in {"start", "serve", "run"}:
        # Import triggers Flask app construction; prefer subprocess for long-lived serve.
        import runpy
        import sys

        mod = "realai.plugins.tools.approval_ui"
        sys.argv = [mod] + list(ctx.get("argv") or [])
        runpy.run_module(mod, run_name="__main__")
        return {"ok": True, "ability": "approval_ui", "action": "start"}

    return {"ok": False, "error": f"unknown_action:{action}", "actions": ["info", "start"]}
