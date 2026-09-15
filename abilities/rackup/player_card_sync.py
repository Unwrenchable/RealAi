"""player_card_sync — thin wrap over ``plugins.rackup_coach.abilities.player_card_sync``.

No second copy of plugin logic. Hive tools and plugin invoke share the card envelope.
"""

from __future__ import annotations

from typing import Any

from ._player import player_from_context

ABILITY = {
    "id": "player_card_sync",
    "name": "player_card_sync",
    "type": "ability",
    "status": "LIVE",
    "source": "plugins.rackup_coach.abilities.player_card_sync",
    "dest": "abilities/rackup/player_card_sync.py",
    "capabilities": ["player_card_sync", "rackup", "unified_player_card"],
    "secrets_policy": "APA token via env/payload hint only — never returned",
}


def run(
    player: Any = None,
    payload: dict[str, Any] | None = None,
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    from plugins.rackup_coach.abilities import player_card_sync as _mod

    if hasattr(player, "player_id"):
        return _mod.run(player, payload or {})

    ctx = dict(context or {})
    ctx.update(kwargs)
    body = dict(ctx.get("payload") or payload or {})
    if input and "name" not in body:
        body["name"] = input
    profile = player_from_context(ctx)
    result = _mod.run(profile, body)
    return {
        "ok": True,
        "ability": "player_card_sync",
        "source": ABILITY["source"],
        "result": result,
    }
