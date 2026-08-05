"""Shared types for RackUp Coach (provider-level; host supplies data)."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional


class RatingBand(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    PRO = "pro"


class Discipline(str, Enum):
    EIGHT_BALL = "eight_ball"
    NINE_BALL = "nine_ball"
    TEN_BALL = "ten_ball"
    STRAIGHT_POOL = "straight_pool"
    ONE_POCKET = "one_pocket"
    BANKS = "banks"
    PYRAMID = "pyramid"  # RackUp Pyramid (classical points on American tables)


# Pyramid skill aliases (may differ from rating-band labels only by source)
class PyramidSkillLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    PRO = "pro"


# Common pool skill tags (weakness / strength keys)
SKILL_TAGS = (
    "break",
    "position_play",
    "cue_ball_control",
    "safety_play",
    "pattern_play",
    "banks",
    "kicks",
    "long_potting",
    "rail_shots",
    "jump_shots",
    "masse",
    "speed_control",
    "english",
    "stance",
    "stroke",
    "pre_shot_routine",
    "mental_focus",
    "match_pressure",
    "table_speed_adapt",
)


def rating_band(rating: float | int | None) -> RatingBand:
    r = float(rating or 0)
    if r < 400:
        return RatingBand.BEGINNER
    if r < 700:
        return RatingBand.INTERMEDIATE
    if r < 900:
        return RatingBand.ADVANCED
    return RatingBand.PRO


@dataclass
class PlayerProfile:
    """Player context supplied by RackUp host — no DB access here."""

    player_id: str
    display_name: str = ""
    rating: float = 500.0
    rating_system: str = "rackup"  # rackup | fargo_est | custom
    discipline: str = Discipline.EIGHT_BALL.value
    preferred_hand: str = "right"
    weaknesses: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    recent_results: list[dict[str, Any]] = field(default_factory=list)
    # e.g. [{"opponent_rating": 620, "won": True, "discipline": "nine_ball"}, ...]
    session_stats: dict[str, Any] = field(default_factory=dict)
    # e.g. balls_made, innings, safeties, scratches
    history_notes: list[str] = field(default_factory=list)
    hall_id: str = ""
    hall_name: str = ""
    table_speed: str = "medium"  # slow | medium | fast
    locale: str = "en"
    # --- RackUp Pyramid ---
    table_size: str = "9ft"  # 7ft → 10-ball rack | 9ft → 15-ball rack
    pyramid_skill: str = ""  # beginner|intermediate|advanced|pro (empty → infer from rating)
    skill_level: str = ""  # alias for pyramid_skill
    pyramid_score: int = 0  # current match score if mid-game
    pyramid_opp_score: int = 0

    @property
    def band(self) -> RatingBand:
        return rating_band(self.rating)

    def effective_pyramid_skill(self) -> str:
        from plugins.rackup_coach.pyramid import normalize_skill

        return normalize_skill(self.pyramid_skill or self.skill_level, rating=self.rating)

    def pyramid_config(self, payload: dict[str, Any] | None = None):
        from plugins.rackup_coach.pyramid import resolve_pyramid

        return resolve_pyramid(player=self, payload=payload)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["band"] = self.band.value
        d["effective_pyramid_skill"] = self.effective_pyramid_skill()
        try:
            d["pyramid"] = self.pyramid_config().to_dict()
        except Exception:
            pass
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PlayerProfile":
        data = dict(data or {})
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class CoachRequest:
    """Unified request envelope for all rackup-coach abilities."""

    ability: str
    player: PlayerProfile
    payload: dict[str, Any] = field(default_factory=dict)
    # free-text goal / chat message when relevant
    goal: str = ""
    organs_enabled: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CoachRequest":
        data = dict(data or {})
        player = PlayerProfile.from_dict(data.get("player") or data.get("profile") or {})
        return cls(
            ability=str(data.get("ability") or data.get("action") or "coach"),
            player=player,
            payload=dict(data.get("payload") or data.get("data") or {}),
            goal=str(data.get("goal") or data.get("message") or data.get("text") or ""),
            organs_enabled=bool(data.get("organs_enabled", True)),
        )


@dataclass
class CoachResponse:
    ok: bool
    ability: str
    result: dict[str, Any] = field(default_factory=dict)
    organ_trace: list[dict[str, Any]] = field(default_factory=list)
    notes: str = ""
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "plugin": "rackup-coach",
            "ability": self.ability,
            "result": self.result,
            "organ_trace": self.organ_trace,
            "notes": self.notes,
            "error": self.error,
        }
