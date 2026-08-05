"""
Multi-game knowledge for RackUp (8-ball, 9-ball, 10-ball, one-pocket, pyramid).

Source of truth: RACKUP_GAME_KNOWLEDGE_AND_AI_CONTRACT.md
"""
from __future__ import annotations

from typing import Any, Optional


# Stable discipline codes
EIGHT_BALL = "eight_ball"
NINE_BALL = "nine_ball"
TEN_BALL = "ten_ball"
ONE_POCKET = "one_pocket"
PYRAMID = "pyramid"

_ALIASES: dict[str, str] = {
    "eight_ball": EIGHT_BALL,
    "8-ball": EIGHT_BALL,
    "8ball": EIGHT_BALL,
    "8_ball": EIGHT_BALL,
    "eight-ball": EIGHT_BALL,
    "nine_ball": NINE_BALL,
    "9-ball": NINE_BALL,
    "9ball": NINE_BALL,
    "9_ball": NINE_BALL,
    "nine-ball": NINE_BALL,
    "ten_ball": TEN_BALL,
    "10-ball": TEN_BALL,
    "10ball": TEN_BALL,
    "10_ball": TEN_BALL,
    "ten-ball": TEN_BALL,
    "one_pocket": ONE_POCKET,
    "one-pocket": ONE_POCKET,
    "onepocket": ONE_POCKET,
    "1-pocket": ONE_POCKET,
    "pyramid": PYRAMID,
    "rackup-pyramid": PYRAMID,
    "rackup_pyramid": PYRAMID,
    "rackuppyramid": PYRAMID,
}


def normalize_discipline(raw: Any, default: str = EIGHT_BALL) -> str:
    if raw is None or raw == "":
        return default
    s = str(raw).strip().lower().replace(" ", "")
    # try direct
    if s in _ALIASES:
        return _ALIASES[s]
    # with underscores/hyphens normalized
    s2 = s.replace("-", "_")
    if s2 in _ALIASES:
        return _ALIASES[s2]
    # fuzzy
    if "pyramid" in s:
        return PYRAMID
    if "pocket" in s:
        return ONE_POCKET
    if "10" in s or "ten" in s:
        return TEN_BALL
    if "9" in s or "nine" in s:
        return NINE_BALL
    if "8" in s or "eight" in s:
        return EIGHT_BALL
    return default


def default_rating_weight(discipline: str, *, skill_level: str = "", table_size: str = "") -> float:
    """Default rating_weight if host omits it. Pyramid uses matrix via pyramid.py."""
    d = normalize_discipline(discipline)
    if d == PYRAMID:
        from plugins.rackup_coach.pyramid import RATING_WEIGHT, normalize_skill

        return float(RATING_WEIGHT.get(normalize_skill(skill_level), 1.0))
    return {
        EIGHT_BALL: 1.0,
        NINE_BALL: 1.0,
        TEN_BALL: 1.05,
        ONE_POCKET: 1.1,
    }.get(d, 1.0)


def skill_band_from_rating(rating: float) -> str:
    """Bands from knowledge doc continuum (not only 400-step internal)."""
    r = float(rating or 500)
    if r < 900:
        return "novice"
    if r < 1500:
        return "intermediate"
    if r < 2100:
        return "advanced"
    return "pro"


# Full game knowledge packs
GAMES: dict[str, dict[str, Any]] = {
    EIGHT_BALL: {
        "id": EIGHT_BALL,
        "display": "8-Ball",
        "objective": (
            "Pocket all of your group (solids 1–7 or stripes 9–15), then legally "
            "pocket the 8-ball in a called pocket."
        ),
        "rack": "15 object balls; 8 in center; solid+stripe at back corners; break from kitchen.",
        "key_rules": [
            "Open table after break until a legal group ball is made.",
            "Your group must be first contact after groups assigned.",
            "8-ball early (before clearing group) is typically a loss.",
            "Scratch while pocketing the 8 is usually a loss if 8 drops.",
            "Call-shot on the 8 is universal in APA/BCA-style play.",
        ],
        "fouls": [
            "Scratch / cue pocketed → BIH (or kitchen per ruleset)",
            "Wrong ball first → foul / BIH",
            "No rail after contact when required",
            "8 early or 8 wrong pocket → loss",
        ],
        "good_play": [
            "Clear easy balls while leaving shape",
            "Keep 8 path open; plan last 2–3 balls",
            "Safety when table is dry",
            "Control cue ball after break",
        ],
        "bad_play": [
            "Chase low-percentage combos early",
            "Block own 8 with own ball",
            "Fire thin cuts with no out",
            "Wild power break with no plan",
        ],
        "coaching_by_band": {
            "novice": "Ghost-ball aim, stop shot, simple patterns, don't leave 8 blocked",
            "intermediate": "2–3 ball patterns, center-ball position, soft vs firm speed",
            "advanced": "Two-way shots, safety exchanges, 8-ball endgame",
            "pro": "Maximum outs, table management, psychological pace",
        },
        "default_rating_weight": 1.0,
        "sotd_focus": ["stop_shot", "pattern_play", "safety_play", "position_play", "break"],
        "validation": {
            "score_type": "race_or_boolean",
            "typical_race": None,
            "notes": "Winner is who wins the game/race; scores may be games won.",
        },
    },
    NINE_BALL: {
        "id": NINE_BALL,
        "display": "9-Ball",
        "objective": "Legally pocket the 9-ball after contacting the lowest numbered ball first.",
        "rack": "Balls 1–9 diamond; 1 on foot spot, 9 in center; break from kitchen.",
        "key_rules": [
            "Always contact lowest numbered ball first.",
            "Push-out after break optional in many codes.",
            "9 on break may win (flag nine_on_break_wins).",
            "Combo/carom onto 9 legal if lowest is first contact.",
            "Scratch → usually BIH table or kitchen (ball_in_hand_mode).",
        ],
        "fouls": ["Scratch", "Wrong ball first", "No rail", "Illegal jump", "Three-foul (some events)"],
        "good_play": [
            "Pattern from high balls back to 9",
            "Two-way safety when stuck",
            "Soft roll for shape after break",
            "Know push-out strategy",
        ],
        "bad_play": [
            "Kill shape leaving thin cuts on 1/2",
            "Always blast 9 early without shape",
            "Break-and-run force with no out",
            "Ignore opponent runout threat",
        ],
        "coaching_by_band": {
            "novice": "Lowest-first discipline, stop/follow basics",
            "intermediate": "3-ball sequences, natural shape",
            "advanced": "Banks, kicks, safety wars, break strategy",
            "pro": "Pattern efficiency, multi-rail position, match pace",
        },
        "default_rating_weight": 1.0,
        "sotd_focus": ["position_play", "cue_ball_control", "safety_play", "break", "kicks"],
        "validation": {
            "score_type": "race",
            "typical_race": 5,
            "notes": "Race formats common (race to 5/7/9).",
        },
    },
    TEN_BALL: {
        "id": TEN_BALL,
        "display": "10-Ball",
        "objective": "Call-shot rotation; win by legally pocketing the called 10 after lowest-first discipline.",
        "rack": "Balls 1–10 triangle; 1 on foot spot, 10 in center.",
        "key_rules": [
            "Call ball and pocket (WPA-style).",
            "Lowest ball first contact.",
            "Early 10 illegally → spot + loss of turn (usually).",
            "Push-out after break often allowed once.",
        ],
        "fouls": ["Scratch", "Wrong ball first", "Uncalled / wrong pocket", "No rail", "Push foul"],
        "good_play": [
            "Precise call-shot discipline",
            "Safety when no out",
            "Controlled break for a ball",
        ],
        "bad_play": [
            "Slop mindset from bar 9-ball",
            "Force thin 10",
            "Wild break with no shot",
        ],
        "coaching_by_band": {
            "novice": "Call accuracy and lowest-first habits",
            "intermediate": "Cue ball for next lowest; basic safeties",
            "advanced": "Multi-rail position; intentional safeties",
            "pro": "Call precision under pressure; pattern efficiency",
        },
        "default_rating_weight": 1.05,
        "sotd_focus": ["pre_shot_routine", "position_play", "safety_play", "cue_ball_control"],
        "validation": {
            "score_type": "race",
            "typical_race": 7,
            "notes": "Stricter call-shot than 9-ball.",
        },
    },
    ONE_POCKET: {
        "id": ONE_POCKET,
        "display": "One Pocket",
        "objective": "Score points by pocketing balls only into your designated corner; typically first to 8.",
        "rack": "15 object balls; breaker/lag winner chooses pocket.",
        "key_rules": [
            "Only your pocket scores for you.",
            "Balls in opponent pocket usually score for them.",
            "Foul may include BIH kitchen + spot/point penalty (foul_penalty).",
            "Defense-first is often correct.",
        ],
        "fouls": ["Scratch", "No rail", "Double hit", "Illegal jump", "Moving balls"],
        "good_play": [
            "Defense and clusters near your pocket",
            "Soft bank / freeze tactics",
            "Count remaining + race math",
            "Safety-first when behind",
        ],
        "bad_play": [
            "Open table for opponent run",
            "Over-aggression early",
            "Ignore scoreboard",
            "Panic offense",
        ],
        "coaching_by_band": {
            "novice": "Which pocket is yours; simple banks; don't scratch",
            "intermediate": "Freezes, clusters, when to dig",
            "advanced": "Multi-ball traps, score management",
            "pro": "Psychological warfare, deep safety, endgame precision",
        },
        "default_rating_weight": 1.1,
        "sotd_focus": ["safety_play", "banks", "mental_focus", "pattern_play"],
        "validation": {
            "score_type": "points_race",
            "typical_race": 8,
            "notes": "race_to defaults to 8 unless host overrides.",
        },
    },
    PYRAMID: {
        "id": PYRAMID,
        "display": "RackUp Pyramid",
        "objective": "First to skill×table points target using classical ball values (1-ball=11).",
        "rack": "7ft→10-ball rack; 9ft→15-ball rack.",
        "key_rules": [
            "Classical scoring: ball N = N points; 1-ball = 11.",
            "Designated cue ball only.",
            "Call-shot by skill matrix (no/optional/yes).",
            "First to points_to_win wins.",
        ],
        "fouls": ["Scratch", "No rail", "Wrong call when required", "Cue fouls"],
        "good_play": [
            "Hunt high value (1-ball=11, high numbers)",
            "Count remaining points",
            "Shape for next high-value",
            "Endgame: know points needed",
        ],
        "bad_play": [
            "Ignore 1-ball premium",
            "Play like 8-ball groups",
            "Kill CB after low ball",
            "Chase impossible combos when short",
        ],
        "coaching_by_band": {
            "novice": "Value of 1-ball; simple pots; count to target",
            "intermediate": "Routes of 2–3 balls; avoid scratches near target",
            "advanced": "Optional call discipline; table-wide value maps",
            "pro": "Mandatory call precision; weight 1.15—mistakes costly",
        },
        "default_rating_weight": None,  # from pyramid matrix
        "sotd_focus": ["pattern_play", "cue_ball_control", "mental_focus", "safety_play"],
        "validation": {
            "score_type": "pyramid_points",
            "typical_race": None,
            "notes": "Use pyramid.py matrix; see locked rules.",
        },
    },
}


def game_knowledge(discipline: Any) -> dict[str, Any]:
    d = normalize_discipline(discipline)
    return dict(GAMES.get(d) or GAMES[EIGHT_BALL])


def coaching_focus(discipline: Any, rating: float) -> str:
    g = game_knowledge(discipline)
    band = skill_band_from_rating(rating)
    return (g.get("coaching_by_band") or {}).get(band) or "Fundamentals and percentage play."


def list_disciplines() -> list[dict[str, str]]:
    return [{"id": g["id"], "display": g["display"]} for g in GAMES.values()]
