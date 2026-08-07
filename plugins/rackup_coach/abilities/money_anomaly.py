"""ROC money_anomaly ability — payment history risk scan (read-only)."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.money_audit import money_anomaly
from plugins.rackup_coach.types import PlayerProfile


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(payload or {})
    if player and player.player_id:
        payload.setdefault("subject_id", player.player_id)
        payload.setdefault("requested_by", player.player_id)
    result = money_anomaly(payload)
    result["requested_by"] = payload.get("requested_by")
    return result
