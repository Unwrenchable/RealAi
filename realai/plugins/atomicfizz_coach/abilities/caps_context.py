"""Stub Caps context — validation hints only.

Caps / vault GPS stay product-owned. This ability returns structured
placeholders so Atomic Fizz can wire the envelope before real intelligence
lands. No GPS fix, no vault lookup, no world mutation.
"""
from __future__ import annotations

from typing import Any


def run(player: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(payload or {})
    player = player or {}
    player_id = player.get("player_id") or player.get("id") or ""
    tenant = payload.get("tenant") or player.get("tenant") or ""

    return {
        "stub": True,
        "player_id": player_id,
        "tenant": tenant,
        "caps": {
            "owned_by": "Atomic Fizz product",
            "gps": None,
            "vault": None,
            "hint": (
                "Caps / vault GPS stay product-owned. RealAI returns "
                "validation hints only — no GPS implementation in this stub."
            ),
        },
        "validation": {
            "ok": True,
            "implemented": False,
            "warnings": [],
            "notes": "Placeholder Caps context — host must supply location/vault facts if they matter.",
        },
        "persist_hint": {
            "owner": "Atomic Fizz product — RealAI does not persist Caps or GPS",
            "fields_to_write": [],
        },
    }
