"""Stub Wrist UI hint — copy/actions placeholders only.

Wrist UI chrome stays product-owned. RealAI may later return hint payloads;
this stub returns a structured empty hint so the host can wire the envelope.
"""
from __future__ import annotations

from typing import Any


def run(player: dict[str, Any], payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(payload or {})
    player = player or {}
    player_id = player.get("player_id") or player.get("id") or ""
    surface = str(payload.get("surface") or "wrist")

    return {
        "stub": True,
        "player_id": player_id,
        "owned_by": "Atomic Fizz Wrist UI",
        "hint": {
            "surface": surface,
            "copy": "Placeholder Wrist UI hint — product renders chrome.",
            "actions": [],
            "priority": "none",
        },
        "notes": "Wrist UI stays product-owned. RealAI returns hints only; no UI ownership.",
        "persist_hint": {
            "owner": "Atomic Fizz product — RealAI does not persist Wrist UI state",
            "fields_to_write": [],
        },
    }
