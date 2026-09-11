"""
RackUp Pyramid — locked game rules (provider-level knowledge).

Table size → rack size:
  7 ft American → 10-ball rack
  9 ft American → 15-ball rack

Skill level → points-to-win, call-shot policy, rating weight.
Classical scoring: pocketed ball scores its number; 1-ball = 11 points.
Designated cue ball only. First to target wins.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from enum import Enum
from typing import Any, Optional


class TableSize(str, Enum):
    FT_7 = "7ft"
    FT_9 = "9ft"


class PyramidSkill(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    PRO = "pro"


# Points-to-win matrix [skill][table]
POINTS_TO_WIN: dict[str, dict[str, int]] = {
    PyramidSkill.BEGINNER.value: {TableSize.FT_7.value: 25, TableSize.FT_9.value: 40},
    PyramidSkill.INTERMEDIATE.value: {TableSize.FT_7.value: 35, TableSize.FT_9.value: 55},
    PyramidSkill.ADVANCED.value: {TableSize.FT_7.value: 45, TableSize.FT_9.value: 71},
    PyramidSkill.PRO.value: {TableSize.FT_7.value: 50, TableSize.FT_9.value: 71},
}

CALL_SHOT: dict[str, str] = {
    PyramidSkill.BEGINNER.value: "no",
    PyramidSkill.INTERMEDIATE.value: "no",
    PyramidSkill.ADVANCED.value: "optional",
    PyramidSkill.PRO.value: "yes",
}

RATING_WEIGHT: dict[str, float] = {
    PyramidSkill.BEGINNER.value: 0.7,
    PyramidSkill.INTERMEDIATE.value: 0.85,
    PyramidSkill.ADVANCED.value: 1.0,
    PyramidSkill.PRO.value: 1.15,
}

RACK_SIZE: dict[str, int] = {
    TableSize.FT_7.value: 10,  # 10-ball rack
    TableSize.FT_9.value: 15,  # 15-ball rack
}

# Classical: ball N scores N, except 1-ball = 11
BALL_VALUES_15: dict[int, int] = {i: (11 if i == 1 else i) for i in range(1, 16)}
BALL_VALUES_10: dict[int, int] = {i: (11 if i == 1 else i) for i in range(1, 11)}


def normalize_table_size(raw: Any) -> str:
    s = str(raw or "9ft").strip().lower().replace(" ", "")
    if s in ("7", "7ft", "7-foot", "7foot", "seven", "bar", "barbox"):
        return TableSize.FT_7.value
    if s in ("9", "9ft", "9-foot", "9foot", "nine", "full", "regulation"):
        return TableSize.FT_9.value
    if "7" in s:
        return TableSize.FT_7.value
    return TableSize.FT_9.value


def normalize_skill(raw: Any, rating: float | None = None) -> str:
    s = str(raw or "").strip().lower()
    aliases = {
        "beg": PyramidSkill.BEGINNER.value,
        "beginner": PyramidSkill.BEGINNER.value,
        "novice": PyramidSkill.BEGINNER.value,
        "int": PyramidSkill.INTERMEDIATE.value,
        "intermediate": PyramidSkill.INTERMEDIATE.value,
        "mid": PyramidSkill.INTERMEDIATE.value,
        "adv": PyramidSkill.ADVANCED.value,
        "advanced": PyramidSkill.ADVANCED.value,
        "pro": PyramidSkill.PRO.value,
        "professional": PyramidSkill.PRO.value,
        "open": PyramidSkill.PRO.value,
    }
    if s in aliases:
        return aliases[s]
    # Infer from rating when skill not provided
    r = float(rating or 0)
    if r <= 0:
        return PyramidSkill.INTERMEDIATE.value
    if r < 400:
        return PyramidSkill.BEGINNER.value
    if r < 700:
        return PyramidSkill.INTERMEDIATE.value
    if r < 900:
        return PyramidSkill.ADVANCED.value
    return PyramidSkill.PRO.value


def ball_value(ball: int, rack_size: int = 15) -> int:
    b = int(ball)
    if b == 1:
        return 11
    if rack_size <= 10 and b > 10:
        return 0
    if b < 1 or b > 15:
        return 0
    return b


def max_rack_points(rack_size: int) -> int:
    """Sum of all ball values if every object ball is pocketed once."""
    vals = BALL_VALUES_10 if rack_size <= 10 else BALL_VALUES_15
    return sum(vals.values())


def points_remaining_to_target(score: int, target: int) -> int:
    return max(0, int(target) - int(score))


def weighted_rating_delta(raw_delta: float, skill: str) -> float:
    """Apply Pyramid rating weight for skill level."""
    w = RATING_WEIGHT.get(normalize_skill(skill), 1.0)
    return float(raw_delta) * w


@dataclass
class PyramidConfig:
    """Resolved Pyramid match/session configuration."""

    table_size: str = TableSize.FT_9.value
    skill_level: str = PyramidSkill.INTERMEDIATE.value
    rack_size: int = 15
    points_to_win: int = 55
    call_shot: str = "no"  # no | optional | yes
    rating_weight: float = 0.85
    scoring: str = "classical"
    cue_ball: str = "designated_only"
    one_ball_value: int = 11
    rules_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["max_single_rack_points"] = max_rack_points(self.rack_size)
        d["ball_values"] = (
            dict(BALL_VALUES_10) if self.rack_size <= 10 else dict(BALL_VALUES_15)
        )
        return d


def resolve_pyramid(
    *,
    table_size: Any = None,
    skill_level: Any = None,
    rating: float | None = None,
    player: Any = None,
    payload: Optional[dict[str, Any]] = None,
) -> PyramidConfig:
    """Resolve Pyramid config from player + payload (host-supplied)."""
    payload = dict(payload or {})
    # Player may be PlayerProfile-like
    p_table = None
    p_skill = None
    p_rating = rating
    if player is not None:
        if hasattr(player, "table_size"):
            p_table = getattr(player, "table_size", None)
        if hasattr(player, "pyramid_skill") or hasattr(player, "skill_level"):
            p_skill = getattr(player, "pyramid_skill", None) or getattr(
                player, "skill_level", None
            )
        if hasattr(player, "rating") and p_rating is None:
            p_rating = float(getattr(player, "rating") or 0)
        if isinstance(player, dict):
            p_table = player.get("table_size") or player.get("table")
            p_skill = player.get("pyramid_skill") or player.get("skill_level")
            if p_rating is None:
                p_rating = float(player.get("rating") or 0)

    # Explicit payload.pyramid or top-level keys
    pyr = dict(payload.get("pyramid") or {})
    ts = normalize_table_size(
        table_size
        or pyr.get("table_size")
        or payload.get("table_size")
        or payload.get("table")
        or p_table
        or "9ft"
    )
    sk = normalize_skill(
        skill_level
        or pyr.get("skill_level")
        or payload.get("skill_level")
        or payload.get("skill")
        or p_skill,
        rating=p_rating,
    )
    rack = RACK_SIZE[ts]
    target = POINTS_TO_WIN[sk][ts]
    call = CALL_SHOT[sk]
    weight = RATING_WEIGHT[sk]

    notes = [
        f"{ts} American table → {rack}-ball rack",
        f"Skill {sk}: first to {target} points wins",
        f"Call shot: {call}",
        f"Rating weight: {weight}×",
        "Classical scoring: ball number = points; 1-ball = 11",
        "Designated cue ball only",
        "Classical mindset still applies on American tables: "
        "value balls, control innings, prefer percentage shape over hero pots",
    ]
    if rack == 10:
        notes.append(
            "10-ball Pyramid: denser value density per ball; "
            "1-ball (11 pts) is a larger swing vs target."
        )
    else:
        notes.append(
            "15-ball Pyramid: more pattern depth; "
            "protect high-value balls (1=11, then 15…9) in traffic."
        )
    if call == "no":
        notes.append("No call-shot: still play intentional lines — count points before shooting.")
    elif call == "optional":
        notes.append("Call-shot optional: practice calling outs in pressure racks.")
    else:
        notes.append("Call-shot required: announce ball and pocket; no slop.")

    return PyramidConfig(
        table_size=ts,
        skill_level=sk,
        rack_size=rack,
        points_to_win=target,
        call_shot=call,
        rating_weight=weight,
        rules_notes=notes,
    )


def score_from_balls(pocketed: list[int], rack_size: int = 15) -> int:
    return sum(ball_value(b, rack_size) for b in pocketed)


def race_context(
    config: PyramidConfig,
    *,
    my_score: int = 0,
    opp_score: int = 0,
) -> dict[str, Any]:
    target = config.points_to_win
    mine_left = points_remaining_to_target(my_score, target)
    opp_left = points_remaining_to_target(opp_score, target)
    return {
        "target": target,
        "my_score": my_score,
        "opp_score": opp_score,
        "my_points_needed": mine_left,
        "opp_points_needed": opp_left,
        "lead": my_score - opp_score,
        "phase": _phase(mine_left, target),
        "high_value_reminder": "1-ball = 11 points — treat as the premium object ball",
        "rack_size": config.rack_size,
        "table_size": config.table_size,
        "skill_level": config.skill_level,
    }


def _phase(points_needed: int, target: int) -> str:
    if target <= 0:
        return "unknown"
    ratio = points_needed / target
    if ratio > 0.66:
        return "opening"
    if ratio > 0.33:
        return "midgame"
    if points_needed > 0:
        return "endgame"
    return "won"


def classical_mindset_tips(config: PyramidConfig) -> list[str]:
    tips = [
        "Count the table: know your score and points still available before every stroke.",
        "The 1-ball is worth 11 — do not gift it; bury or take when percentage is high.",
        "Designated cue ball only: protect CB position like classical billiards.",
        "American table, classical brain: percentage over highlight-reel pots.",
    ]
    if config.rack_size == 10:
        tips.append(
            f"On 7ft/10-ball, target is {config.points_to_win}: "
            "fewer balls means each miss costs more race share."
        )
        tips.append("Cluster management is tighter — plan two-ball shapes, not five-ball dreams.")
    else:
        tips.append(
            f"On 9ft/15-ball, target is {config.points_to_win}: "
            "use full-rack patterns and hold high numbers for key innings."
        )
        tips.append("Open traffic early; isolate 1-ball (11) and top numbers when safe.")
    if config.skill_level in ("beginner", "intermediate"):
        tips.append("No call-shot required — still pick a pocket mentally to build pro habits.")
    if config.skill_level == "advanced":
        tips.append("Call-shot optional: call critical outs to train tournament discipline.")
    if config.skill_level == "pro":
        tips.append("Call-shot on: every intentional ball/pocket; safeties must be clean.")
    return tips


def pyramid_matrix() -> dict[str, Any]:
    """Full locked rules matrix for hosts / docs."""
    rows = []
    for skill in (
        PyramidSkill.BEGINNER.value,
        PyramidSkill.INTERMEDIATE.value,
        PyramidSkill.ADVANCED.value,
        PyramidSkill.PRO.value,
    ):
        rows.append(
            {
                "skill_level": skill,
                "7ft_10ball_points": POINTS_TO_WIN[skill][TableSize.FT_7.value],
                "9ft_15ball_points": POINTS_TO_WIN[skill][TableSize.FT_9.value],
                "call_shot": CALL_SHOT[skill],
                "rating_weight": RATING_WEIGHT[skill],
            }
        )
    return {
        "game": "RackUp Pyramid",
        "table_to_rack": {"7ft": 10, "9ft": 15},
        "scoring": {
            "type": "classical",
            "ball_n": "scores n",
            "ball_1": 11,
            "cue_ball": "designated_only",
            "win": "first_to_target",
        },
        "skill_matrix": rows,
    }
