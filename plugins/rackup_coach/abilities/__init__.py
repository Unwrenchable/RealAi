"""RackUp Coach ability modules."""
from __future__ import annotations

from typing import Any, Callable

from plugins.rackup_coach.types import PlayerProfile

from . import (
    coach,
    hall_context,
    matchmaking,
    moderation,
    rating_intel,
    shot_of_the_day,
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
}


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
