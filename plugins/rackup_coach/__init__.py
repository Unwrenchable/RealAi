"""
RackUp Coach — RealAI living plugin
===================================
Plugin id: ``rackup-coach``
Package:   ``plugins.rackup_coach``

Provider-level pool coaching + platform intelligence.
Uses synthetic organs via ``organs_bridge`` / hive.
"""
from __future__ import annotations

from typing import Any, Optional

from plugins.rackup_coach.coach_agent import COACH, RackUpCoachAgent
from plugins.rackup_coach.types import CoachRequest, CoachResponse, PlayerProfile

__all__ = [
    "COACH",
    "RackUpCoachAgent",
    "CoachRequest",
    "CoachResponse",
    "PlayerProfile",
    "invoke",
    "register",
    "METADATA",
]

METADATA = {
    "name": "rackup-coach",
    "version": "1.1.0",
    "capabilities": [
        "professional_coach",
        "shot_of_the_day",
        "video_analysis",
        "chat_moderation",
        "matchmaking_support",
        "rating_intelligence",
        "tournament_insights",
        "hall_session_context",
        "mental_game",
        "practice_plans",
        "rackup_pyramid",
        "pyramid_rules",
        "classical_scoring",
    ],
    "methods": [
        "invoke",
        "shot_of_the_day",
        "moderate",
        "coach",
        "pyramid",
        "pyramid_rules",
        "video_analysis",
        "matchmaking",
        "rating_intel",
        "tournament",
        "hall_context",
    ],
    "pyramid": {
        "7ft": {"rack": 10, "points": {"beginner": 25, "intermediate": 35, "advanced": 45, "pro": 50}},
        "9ft": {"rack": 15, "points": {"beginner": 40, "intermediate": 55, "advanced": 71, "pro": 71}},
        "call_shot": {"beginner": "no", "intermediate": "no", "advanced": "optional", "pro": "yes"},
        "rating_weight": {"beginner": 0.7, "intermediate": 0.85, "advanced": 1.0, "pro": 1.15},
        "scoring": {"1_ball": 11, "cue": "designated_only", "style": "classical"},
    },
}


def invoke(data: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Primary entry — RackUp host calls this with ability + player + payload."""
    req = CoachRequest.from_dict(data or {})
    return COACH.handle(req).to_dict()


def register(model=None, config=None) -> dict[str, Any]:
    """Register plugin methods on a RealAI model instance (sample_plugin style)."""
    config = config or {}

    def _invoke(data=None):
        return invoke(data)

    def _sotd(data=None):
        data = dict(data or {})
        data["ability"] = "shot_of_the_day"
        return invoke(data)

    def _mod(data=None):
        data = dict(data or {})
        data["ability"] = "moderation"
        return invoke(data)

    def _coach(data=None):
        data = dict(data or {})
        data.setdefault("ability", "coach")
        return invoke(data)

    if model is not None:
        setattr(model, "rackup_coach", _invoke)
        setattr(model, "rackup_shot_of_the_day", _sotd)
        setattr(model, "rackup_moderate", _mod)
        setattr(model, "rackup_coach_session", _coach)

    meta = dict(METADATA)
    meta["config"] = config
    meta["ok"] = True
    return meta
