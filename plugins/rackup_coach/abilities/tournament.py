"""Tournament / league insights (Pyramid-aware)."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.pyramid import classical_mindset_tips, resolve_pyramid
from plugins.rackup_coach.types import PlayerProfile


def tournament_insights(
    player: PlayerProfile,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Host payload may include:
      event: {name, format, field_size, race_to, discipline, table_size, skill_level}
      bracket_position: string
      upcoming_opponent: {rating, style}
    """
    payload = payload or {}
    event = dict(payload.get("event") or {})
    opp = dict(payload.get("upcoming_opponent") or {})
    fmt = str(event.get("format") or "single_elim").lower()
    # Merge event pyramid fields into payload for resolve
    pyr_payload = {
        **payload,
        "table_size": event.get("table_size") or payload.get("table_size"),
        "skill_level": event.get("skill_level") or payload.get("skill_level"),
        "pyramid": payload.get("pyramid") or event.get("pyramid"),
    }
    cfg = resolve_pyramid(player=player, payload=pyr_payload)
    is_pyramid = (
        str(event.get("discipline") or player.discipline or "").lower() == "pyramid"
        or bool(event.get("pyramid") or payload.get("game") == "pyramid")
    )
    race = event.get("race_to") or payload.get("race_to") or (
        cfg.points_to_win if is_pyramid else 5
    )

    prep = [
        f"Warm up 25–40 min with discipline={event.get('discipline') or player.discipline}",
        "Map first-rack plan: break preference + safety bailout",
        "Hydration + chalk + tip check before lag",
    ]
    if is_pyramid:
        prep = [
            f"Pyramid warm-up on {cfg.table_size} ({cfg.rack_size}-ball rack)",
            f"Rehearse first-to-{cfg.points_to_win}; call_shot={cfg.call_shot}",
            "Count drill: verbalize points needed for 5 minutes",
            "1-ball (11 pts) decision reps: take vs bury",
            "Chalk + tip + designated CB check before lag",
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

    if is_pyramid:
        strategic = [
            f"Race is points-to-{cfg.points_to_win} on {cfg.rack_size}-ball rack "
            f"(rating weight {cfg.rating_weight}×).",
            "Classical scoring on American table — percentage over hero pots.",
        ] + strategic

    return {
        "player_id": player.player_id,
        "band": player.band.value,
        "event": event,
        "race_to": race,
        "format": fmt,
        "prep_checklist": prep,
        "strategic_notes": strategic,
        "league": league,
        "pyramid": cfg.to_dict() if is_pyramid else None,
        "classical_mindset": classical_mindset_tips(cfg) if is_pyramid else [],
        "mental": [
            "Between games: one tactical note max, then breathe",
            "Never discuss money or side bets at the table",
            "Re-state points-needed before each Pyramid break" if is_pyramid else "Stay in routine",
        ],
    }


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return tournament_insights(player, payload)
