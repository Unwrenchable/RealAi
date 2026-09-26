"""ROC payout_sanity ability — standings vs payout lines (read-only)."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.money_audit import payout_sanity
from plugins.rackup_coach.types import PlayerProfile


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(payload or {})
    if player and player.player_id and "requested_by" not in payload:
        payload["requested_by"] = player.player_id
    result = payout_sanity(payload)
    result["requested_by"] = payload.get("requested_by")
    return result
