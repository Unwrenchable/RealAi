"""ROC money_anomaly ability — payment history risk scan (read-only)."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.money_audit import money_anomaly
from plugins.rackup_coach.types import PlayerProfile


# merged 2026-10-16 (MERGE_LEDGER: rackup_coach/money_anomaly) metadata from abilities/rackup/money_anomaly.py; read-only, never authorizes payouts
ABILITY = {
    "id": "money_anomaly",
    "name": "money_anomaly",
    "type": "ability",
    "status": "CODE",
    "source": "realai.plugins.rackup_coach.abilities.money_anomaly",
    "dest": "realai/plugins/rackup_coach/abilities/money_anomaly.py",
    "capabilities": ["money_anomaly", "rackup"],
    "secrets_policy": "none — no wallet/key promotion",
    "read_only": True,
    "authorize_payout": False,
}


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(payload or {})
    if player and player.player_id:
        payload.setdefault("subject_id", player.player_id)
        payload.setdefault("requested_by", player.player_id)
    result = money_anomaly(payload)
    result["requested_by"] = payload.get("requested_by")
    return result
