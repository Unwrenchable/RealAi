"""Tournament / league insights."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.types import PlayerProfile


def tournament_insights(
    player: PlayerProfile,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Host payload may include:
      event: {name, format, field_size, race_to, discipline}
      bracket_position: string
      upcoming_opponent: {rating, style}
    """
    payload = payload or {}
    event = dict(payload.get("event") or {})
    opp = dict(payload.get("upcoming_opponent") or {})
    fmt = str(event.get("format") or "single_elim").lower()
    race = event.get("race_to") or payload.get("race_to") or 5

    prep = [
        f"Warm up 25–40 min with discipline={event.get('discipline') or player.discipline}",
        "Map first-rack plan: break preference + safety bailout",
        "Hydration + chalk + tip check before lag",
    ]
    if fmt in ("double_elim", "double_elimination"):
        prep.append("Pace yourself — winners side aggression, losers side patience.")
    if int(race) >= 7:
        prep.append("Long race: track table speed changes mid-match.")

    strategic = []
    if opp.get("rating"):
        delta = float(opp["rating"]) - float(player.rating)
        if delta > 40:
            strategic.append("Uphill: extend safety exchanges; wait for mistakes.")
        elif delta < -40:
            strategic.append("Favorite: apply pressure early; avoid exhibition shots.")
        else:
            strategic.append("Coin-flip skill — lag and break box decide early racks.")
    else:
        strategic.append("Unknown opponent: open with controlled break and read table speed.")

    league = {
        "standings_advice": "Protect rating integrity — no tanking; report disputes in-app only.",
        "weekly_focus": (player.weaknesses or ["position_play", "safety_play"])[:2],
    }

    return {
        "player_id": player.player_id,
        "band": player.band.value,
        "event": event,
        "race_to": race,
        "format": fmt,
        "prep_checklist": prep,
        "strategic_notes": strategic,
        "league": league,
        "mental": [
            "Between games: one tactical note max, then breathe",
            "Never discuss money or side bets at the table",
        ],
    }


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return tournament_insights(player, payload)
