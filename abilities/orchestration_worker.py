"""Thin wrap over ``modules.orchestrators.orchestration_worker`` (approval poll loop)."""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "orchestration_worker",
    "name": "orchestration_worker",
    "type": "ability",
    "status": "CODE",
    "source": "modules.orchestrators.orchestration_worker",
    "dest": "abilities/orchestration_worker.py",
    "capabilities": ["orchestration", "approval", "worker", "patch_apply"],
    "secrets_policy": "optional SLACK_*/TEAMS_WEBHOOK / GITHUB_TOKEN",
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
            "ability": "orchestration_worker",
            "impl": "modules.orchestrators.orchestration_worker",
            "run": "python -m modules.orchestrators.orchestration_worker",
            "launcher": "start_orchestration_worker.bat",
            "compat_shim": "repo_tools/orchestration_worker.py",
            "actions": ["info", "tick", "start"],
            "pairs_with": ["approval_store", "approval_ui", "notifier"],
        }

    if action == "tick":
        from modules.orchestrators.orchestration_worker import _tick

        _tick()
        return {"ok": True, "ability": "orchestration_worker", "action": "tick"}

    if action in {"start", "run", "loop"}:
        from modules.orchestrators.orchestration_worker import main_loop

        main_loop()
        return {"ok": True, "ability": "orchestration_worker", "action": "start"}

    return {
        "ok": False,
        "error": f"unknown_action:{action}",
        "actions": ["info", "tick", "start"],
    }

