"""Atomic Fizz Coach stub ability modules."""
from __future__ import annotations

from typing import Any, Callable

from . import caps_context, health, wrist_ui_hint

ABILITY_RUNNERS: dict[str, Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]] = {
    "health": health.run,
    "ping": health.run,
    "caps_context": caps_context.run,
    "caps": caps_context.run,
    "wrist_ui_hint": wrist_ui_hint.run,
    "wrist_ui": wrist_ui_hint.run,
    "wrist": wrist_ui_hint.run,
}


def run_ability(
    name: str,
    player: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    key = (name or "health").strip().lower()
    fn = ABILITY_RUNNERS.get(key)
    if not fn:
        return {
            "error": f"unknown ability '{name}'",
            "available": sorted(set(ABILITY_RUNNERS)),
        }
    return fn(player or {}, payload or {})


__all__ = ["ABILITY_RUNNERS", "run_ability"]
