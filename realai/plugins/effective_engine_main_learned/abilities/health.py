"""Stub ability `health` — learned from git-learn (no runtime heal)."""
from __future__ import annotations

from typing import Any

# REALAI_LEARNED_STUB

PLUGIN_ID = "effective-engine-main-learned"
PLUGIN_VERSION = "0.1.0"
ABILITY_ID = "health"
ALIASES = ('ping',)


def run(player: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    return {
        "status": "ok",
        "plugin": PLUGIN_ID,
        "ability": ABILITY_ID,
        "version": PLUGIN_VERSION,
        "stub": True,
        "learned": True,
        "heal": False,
        "description": 'Stub liveness / contract discovery (no runtime heal)',
        "player_id": (player or {}).get("player_id") or (player or {}).get("id") or "",
        "notes": "Placeholder learned ability — contract discovery only; no runtime heal.",
        "echo": {
            "payload_keys": sorted(str(k) for k in payload.keys()),
        },
    }
