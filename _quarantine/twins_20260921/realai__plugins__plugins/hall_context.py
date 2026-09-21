"""Hall / ROC session context awareness (Pyramid table size aware)."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.pyramid import resolve_pyramid
from plugins.rackup_coach.roc import extract_roc_context, format_coaching_notes
from plugins.rackup_coach.types import PlayerProfile


def hall_session_context(
    player: PlayerProfile,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Host may send:
      hall: {id, name, tables, noise_level, cloth, pockets, table_size}
      session: {started_at, games_played, fatigue?, lighting?, game?, roc session ids}
      roc / format / roc_league_id for ROC nights
    """
    payload = payload or {}
    roc = extract_roc_context(player, payload)
    hall = dict(payload.get("hall") or {})
    session = dict(payload.get("session") or {})

    hall_id = hall.get("id") or player.hall_id or ""
    hall_name = hall.get("name") or player.hall_name or "unknown hall"
    cloth = str(hall.get("cloth") or player.table_speed or "medium")
    noise = str(hall.get("noise_level") or "moderate")
    games = int(session.get("games_played") or 0)

    # Infer table size from hall if provided
    table_hint = hall.get("table_size") or session.get("table_size") or player.table_size
    pyr_payload = {**payload, "table_size": table_hint}
    cfg = resolve_pyramid(player=player, payload=pyr_payload)

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

    adaptations.append(
        f"Pyramid context: {cfg.table_size} → {cfg.rack_size}-ball rack, "
        f"skill={cfg.skill_level}, first to {cfg.points_to_win}, "
        f"call_shot={cfg.call_shot}."
    )
    if cfg.rack_size == 10:
        adaptations.append("Bar-box 7ft: tighter patterns; value density high per ball.")
    else:
        adaptations.append("9ft full table: use pattern depth; isolate premium numbers.")

    if roc.get("is_roc") or roc.get("format"):
        adaptations.append(
            f"ROC session: format={roc.get('format_display') or roc.get('format') or 'unknown'} "
            f"— continuous rating ladder; ledger/payouts owned by RackUp."
        )
        for tip in format_coaching_notes(roc.get("format"), roc.get("game_style")):
            adaptations.append(tip)

    return {
        "player_id": player.player_id,
        "hall_id": hall_id,
        "hall_name": hall_name,
        "table_speed": cloth,
        "noise_level": noise,
        "session": session,
        "pyramid": cfg.to_dict(),
        "roc": {
            "is_roc": bool(roc.get("is_roc") or roc.get("format")),
            "roc_league_id": roc.get("roc_league_id") or session.get("roc_league_id"),
            "season_id": roc.get("season_id") or session.get("season_id"),
            "session_id": roc.get("session_id") or session.get("id") or session.get("session_id"),
            "format": roc.get("format") or session.get("format"),
            "format_display": roc.get("format_display"),
            "format_config": roc.get("format_config"),
            "game_style": roc.get("game_style"),
        },
        "adaptations": adaptations,
        "equipment_check": [
            "Tip chalked and shaped",
            "Shaft clean",
            "Bridge hand dry",
            "Designated cue ball only (Pyramid)",
            f"Confirm table size {cfg.table_size} / rack {cfg.rack_size} at {hall_name}",
        ],
    }


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return hall_session_context(player, payload)
