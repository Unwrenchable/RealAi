"""ROC ledger_audit ability — read-only session/season money audit."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.money_audit import ledger_audit
from plugins.rackup_coach.types import PlayerProfile


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(payload or {})
    # Optional: tag requesting operator from player context
    if player and player.player_id and "requested_by" not in payload:
        payload["requested_by"] = player.player_id
    result = ledger_audit(payload)
    result["requested_by"] = payload.get("requested_by")
    return result
