"""ROC ledger audit — wraps ``plugins.rackup_coach.abilities.ledger_audit``.

Read-only session/season money audit. Does not move funds or persist secrets.
"""

from __future__ import annotations

from typing import Any

from ._player import player_from_context

ABILITY = {
    "id": "ledger_audit",
    "name": "ledger_audit",
    "type": "ability",
    "status": "CODE",
    "source": "plugins.rackup_coach.abilities.ledger_audit",
    "dest": "abilities/rackup/ledger_audit.py",
    "capabilities": ["ledger_audit", "money_anomaly_review", "session_season_audit"],
    "secrets_policy": "none — audit payloads only; never promote wallet keys",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Run a read-only ledger audit for the requesting player/operator."""
    from plugins.rackup_coach.abilities import ledger_audit as _ledger

    ctx = dict(context or {})
    ctx.update(kwargs)
    payload = dict(ctx.get("payload") or {})
    for key in ("session", "season", "entries", "requested_by"):
        if key in ctx and key not in payload:
            payload[key] = ctx[key]
    if input and "note" not in payload:
        payload["note"] = input
    player = player_from_context(ctx)
    result = _ledger.run(player, payload)
    return {
        "ok": True,
        "ability": "ledger_audit",
        "source": ABILITY["source"],
        "result": result,
    }
