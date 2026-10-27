"""ROC ledger_audit ability — read-only session/season money audit."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.money_audit import ledger_audit
from plugins.rackup_coach.types import PlayerProfile


# merged 2026-10-16 (MERGE_LEDGER: rackup_coach/ledger_audit) metadata from abilities/rackup/ledger_audit.py; read-only, never authorizes payouts
ABILITY = {
    "id": "ledger_audit",
    "name": "ledger_audit",
    "type": "ability",
    "status": "CODE",
    "source": "realai.plugins.rackup_coach.abilities.ledger_audit",
    "dest": "realai/plugins/rackup_coach/abilities/ledger_audit.py",
    "capabilities": ["ledger_audit", "money_anomaly_review", "session_season_audit"],
    "secrets_policy": "none — audit payloads only; never promote wallet keys",
    "read_only": True,
    "authorize_payout": False,
}


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(payload or {})
    # Optional: tag requesting operator from player context
    if player and player.player_id and "requested_by" not in payload:
        payload["requested_by"] = player.player_id
    result = ledger_audit(payload)
    result["requested_by"] = payload.get("requested_by")
    return result
