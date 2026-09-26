"""RackUp Coach ability modules."""
from __future__ import annotations

from typing import Any, Callable

from plugins.rackup_coach.types import PlayerProfile

from . import (
    coach,
    hall_context,
    ledger_audit,
    league_validate,
    matchmaking,
    moderation,
    money_anomaly,
    payout_sanity,
    pyramid_rules,
    rating_convert,
    rating_intel,
    rating_update,
    shot_of_the_day,
    sotd_contribute,
    tournament,
    video_analysis,
)

ABILITY_RUNNERS: dict[str, Callable[[PlayerProfile, dict[str, Any]], dict[str, Any]]] = {
    "coach": lambda p, d: coach.run(p, d, goal=str(d.get("goal") or "")),
    "professional_coach": lambda p, d: coach.run(p, d, goal=str(d.get("goal") or "")),
    "practice_plans": lambda p, d: coach.run(p, {**d, "mode": "practice_plan"}),
    "mental_game": lambda p, d: coach.run(p, {**d, "mode": "mental"}),
    "pre_match_prep": lambda p, d: coach.run(p, {**d, "mode": "pre_match"}),
    "pattern_recognition": lambda p, d: coach.run(p, {**d, "mode": "pattern"}),
    "pyramid": lambda p, d: coach.run(p, {**d, "mode": "pyramid", "game": "pyramid"}),
    "pyramid_coach": lambda p, d: coach.run(p, {**d, "mode": "pyramid", "game": "pyramid"}),
    "pyramid_rules": pyramid_rules.run,
    "pyramid_matrix": pyramid_rules.run,
    "shot_of_the_day": shot_of_the_day.run,
    "sotd": shot_of_the_day.run,
    "moderation": moderation.run,
    "moderate": moderation.run,
    "chat_moderation": moderation.run,
    "video_analysis": video_analysis.run,
    "video": video_analysis.run,
    "matchmaking": matchmaking.run,
    "matchmaking_support": matchmaking.run,
    "rating_intel": rating_intel.run,
    "rating_intelligence": rating_intel.run,
    "tournament": tournament.run,
    "tournament_insights": tournament.run,
    "hall_context": hall_context.run,
    "hall_session_context": hall_context.run,
    "rating_update": rating_update.run,
    "skill_update": rating_update.run,
    "post_match_rating": rating_update.run,
    "league_validate": league_validate.run,
    "league_score": league_validate.run,
    "score_validate": league_validate.run,
    "sotd_contribute": sotd_contribute.run,
    "shot_library_contribute": sotd_contribute.run,
    "rating_convert": rating_convert.run,
    "league_convert": rating_convert.run,
    "convert_rating": rating_convert.run,
    "game_knowledge": lambda p, d: _game_knowledge_ability(p, d),
    "roc_info": lambda p, d: _roc_info_ability(p, d),
    "roc": lambda p, d: _roc_info_ability(p, d),
    # ROC money audit (read-only — never moves money)
    "ledger_audit": ledger_audit.run,
    "audit_ledger": ledger_audit.run,
    "roc_ledger_audit": ledger_audit.run,
    "payout_sanity": payout_sanity.run,
    "payout_audit": payout_sanity.run,
    "sanity_payout": payout_sanity.run,
    "money_anomaly": money_anomaly.run,
    "anomaly_scan": money_anomaly.run,
    "payment_anomaly": money_anomaly.run,
}


def _game_knowledge_ability(player: PlayerProfile, payload: dict[str, Any]) -> dict[str, Any]:
    from plugins.rackup_coach.games import game_knowledge, list_disciplines, normalize_discipline

    disc = normalize_discipline(
        (payload or {}).get("discipline")
        or (payload or {}).get("game")
        or (payload or {}).get("game_style")
        or player.discipline
    )
    out = dict(game_knowledge(disc))
    out["disciplines"] = list_disciplines()
    out["normalized_discipline"] = disc
    return out


def _roc_info_ability(player: PlayerProfile, payload: dict[str, Any]) -> dict[str, Any]:
    """Discoverability for ROC host integration."""
    from plugins.rackup_coach.leagues import display_band, format_rating_chip
    from plugins.rackup_coach.roc import (
        FORMATS_ORDERED,
        FORMAT_DISPLAY,
        GAME_STYLES,
        extract_roc_context,
        format_config,
        format_coaching_notes,
        roc_provider_boundary,
    )

    ctx = extract_roc_context(player, payload or {})
    fmt = ctx.get("format")
    from plugins.rackup_coach.glicko2 import system_info

    return {
        "brand": "ROC — Rack of Champions",
        "hierarchy": "RackUp = platform · ROC = competitive league system",
        "formats_ordered": list(FORMATS_ORDERED),
        "format_display": dict(FORMAT_DISPLAY),
        "game_styles": list(GAME_STYLES),
        "format_config": format_config(fmt) if fmt else {f: format_config(f) for f in FORMATS_ORDERED},
        "context": ctx,
        "player_chip": format_rating_chip(player.rating),
        "player_band_label": display_band(player.rating),
        "player_rd": getattr(player, "rd", None),
        "player_volatility": getattr(player, "volatility", None),
        "ladder": system_info(),
        "format_coaching_notes": format_coaching_notes(fmt, ctx.get("game_style") or player.discipline),
        "provider_boundary": roc_provider_boundary(),
        "abilities": [
            "league_validate",
            "rating_update",
            "rating_convert",
            "matchmaking",
            "coach",
            "pyramid",
            "shot_of_the_day",
            "moderation",
            "video_analysis",
            "pyramid_rules",
            "hall_context",
            "ledger_audit",
            "payout_sanity",
            "money_anomaly",
        ],
        "money_audit": {
            "read_only": True,
            "owns_ledger": False,
            "authorize_payout": False,
            "gate": "RackUp must call ledger_audit (+ payout_sanity) before auto-payout release",
        },
    }


# ensure type for helper
from typing import Any  # noqa: E402  — used by _game_knowledge_ability


def run_ability(name: str, player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    key = (name or "coach").strip().lower()
    fn = ABILITY_RUNNERS.get(key)
    if not fn:
        return {
            "error": f"unknown ability '{name}'",
            "available": sorted(set(ABILITY_RUNNERS)),
        }
    return fn(player, payload or {})


__all__ = ["ABILITY_RUNNERS", "run_ability"]
