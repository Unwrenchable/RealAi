"""Stub health ability — liveness + contract discovery only.

This is not a runtime heal. No organs, no self-repair, no game world mutation.
"""
from __future__ import annotations

from typing import Any

PLUGIN_ID = "atomicfizz-coach"
PLUGIN_VERSION = "0.1.0"
ABILITIES = ("health", "caps_context", "wrist_ui_hint")


def run(player: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    return {
        "status": "ok",
        "plugin": PLUGIN_ID,
        "version": PLUGIN_VERSION,
        "stub": True,
        "heal": False,
        "abilities": list(ABILITIES),
        "player_id": (player or {}).get("player_id") or (player or {}).get("id") or "",
        "notes": "Placeholder health — contract discovery only; no runtime heal.",
        "echo": {
            "payload_keys": sorted(str(k) for k in payload.keys()),
        },
    }
