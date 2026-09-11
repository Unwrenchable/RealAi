"""Thin wrap over ``realai.plugins.tools.notifier`` (Slack / Teams webhooks)."""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "notifier",
    "name": "notifier",
    "type": "ability",
    "status": "CODE",
    "source": "realai.plugins.tools.notifier",
    "dest": "abilities/notifier.py",
    "capabilities": ["notify", "slack", "teams", "webhooks"],
    "secrets_policy": "optional SLACK_WEBHOOK / SLACK_BOT_TOKEN / TEAMS_WEBHOOK",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    from realai.plugins.tools.notifier import Notifier

    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or "notify").lower().strip()
    message = str(ctx.get("message") or input or "").strip()
    title = ctx.get("title")

    n = Notifier(
        slack_webhook=ctx.get("slack_webhook"),
        teams_webhook=ctx.get("teams_webhook"),
        bot_token=ctx.get("bot_token"),
    )

    if action in {"info", "status", "help"}:
        return {
            "ok": True,
            "ability": "notifier",
            "impl": "realai.plugins.tools.notifier.Notifier",
            "configured": {
                "slack_webhook": bool(getattr(n, "_slack_webhook", None)),
                "teams_webhook": bool(getattr(n, "_teams_webhook", None)),
                "bot_token": bool(getattr(n, "_bot_token", None)),
            },
            "actions": ["notify", "info"],
        }

    if action in {"notify", "send", ""}:
        if not message:
            return {"ok": False, "error": "message required"}
        n.notify(message, title=title)
        return {"ok": True, "ability": "notifier", "action": "notify", "sent": True}

    return {"ok": False, "error": f"unknown_action:{action}", "actions": ["notify", "info"]}
