"""Hall / session context awareness."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.types import PlayerProfile


def hall_session_context(
    player: PlayerProfile,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Host may send:
      hall: {id, name, tables, noise_level, cloth, pockets}
      session: {started_at, games_played, fatigue?, lighting?}
    """
    payload = payload or {}
    hall = dict(payload.get("hall") or {})
    session = dict(payload.get("session") or {})

    hall_id = hall.get("id") or player.hall_id or ""
    hall_name = hall.get("name") or player.hall_name or "unknown hall"
    cloth = str(hall.get("cloth") or player.table_speed or "medium")
    noise = str(hall.get("noise_level") or "moderate")
    games = int(session.get("games_played") or 0)

    adaptations = []
    if cloth.lower() in ("fast", "slick"):
        adaptations.append("Fast cloth: shorter draw, earlier speed down on shape.")
    elif cloth.lower() in ("slow", "sticky", "new_cloth"):
        adaptations.append("Slow cloth: commit to firmer stun; leave more angle.")
    else:
        adaptations.append("Medium cloth: default natural roll lines.")

    if noise.lower() in ("high", "loud", "busy"):
        adaptations.append("High noise: tighten PSR; use ear isolation if allowed.")
    if games >= 6:
        adaptations.append("Session fatigue risk: shorten stroke; re-check stance each rack.")
    if games == 0:
        adaptations.append("Cold start: 10-ball warm-up before rated play.")

    return {
        "player_id": player.player_id,
        "hall_id": hall_id,
        "hall_name": hall_name,
        "table_speed": cloth,
        "noise_level": noise,
        "session": session,
        "adaptations": adaptations,
        "equipment_check": [
            "Tip chalked and shaped",
            "Shaft clean",
            "Bridge hand dry",
            f"Note pocket tightness if observed at {hall_name}",
        ],
    }


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return hall_session_context(player, payload)
