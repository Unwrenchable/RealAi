"""ROC payout_sanity ability — standings vs payout lines (read-only)."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.money_audit import payout_sanity
from plugins.rackup_coach.types import PlayerProfile


# merged 2026-10-16 (MERGE_LEDGER: rackup_coach/payout_sanity) metadata from abilities/rackup/payout_sanity.py; read-only, never authorizes payouts
ABILITY = {
    "id": "payout_sanity",
    "name": "payout_sanity",
    "type": "ability",
    "status": "CODE",
    "source": "realai.plugins.rackup_coach.abilities.payout_sanity",
    "dest": "realai/plugins/rackup_coach/abilities/payout_sanity.py",
    "capabilities": ["payout_sanity", "rackup"],
    "secrets_policy": "none — no wallet/key promotion",
    "read_only": True,
    "authorize_payout": False,
}


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(payload or {})
    if player and player.player_id and "requested_by" not in payload:
        payload["requested_by"] = player.player_id
    result = payout_sanity(payload)
    result["requested_by"] = payload.get("requested_by")
    return result
