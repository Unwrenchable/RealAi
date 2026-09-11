"""Adapter for the rackup-coach living plugin."""
from __future__ import annotations

from typing import Any, Optional


def invoke_rackup_coach(data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    from plugins.rackup_coach import invoke

    return invoke(data or {})


def shot_of_the_day(player: dict[str, Any], **payload: Any) -> dict[str, Any]:
    return invoke_rackup_coach(
        {"ability": "shot_of_the_day", "player": player, "payload": payload}
    )


def moderate(text: str, player: Optional[dict[str, Any]] = None, **ctx: Any) -> dict[str, Any]:
    return invoke_rackup_coach(
        {
            "ability": "moderation",
            "player": player or {"player_id": "anon"},
            "payload": {"text": text, "context": ctx},
        }
    )


def coach(player: dict[str, Any], mode: str = "full", goal: str = "", **payload: Any) -> dict[str, Any]:
    return invoke_rackup_coach(
        {
            "ability": "coach",
            "player": player,
            "goal": goal,
            "payload": {"mode": mode, **payload},
        }
    )


def rackup_coach_status() -> dict[str, Any]:
    try:
        from plugins.rackup_coach import METADATA

        return {"ok": True, "plugin": METADATA}
    except Exception as e:
        return {"ok": False, "error": str(e)}
