"""Professional coach — basic through pro, rating-aware + RackUp Pyramid."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.games import (
    coaching_focus,
    game_knowledge,
    normalize_discipline,
    skill_band_from_rating,
)
from plugins.rackup_coach.pyramid import (
    classical_mindset_tips,
    race_context,
    resolve_pyramid,
)
from plugins.rackup_coach.types import PlayerProfile, RatingBand


_BAND_CURRICULUM: dict[RatingBand, dict[str, Any]] = {
    RatingBand.BEGINNER: {
        "focus": ["stance", "stroke", "stop_shot", "center_ball", "pre_shot_routine"],
        "session_minutes": 45,
        "intensity": "foundations",
        "message": "Build a repeatable stroke and own stop / follow before fancy english.",
    },
    RatingBand.INTERMEDIATE: {
        "focus": ["position_play", "pattern_play", "soft_follow", "simple_safety", "break"],
        "session_minutes": 60,
        "intensity": "link_skills",
        "message": "Connect cue-ball control to three-ball outs and two-way safeties.",
    },
    RatingBand.ADVANCED: {
        "focus": ["key_ball", "cluster_management", "long_stun", "kicks", "match_tempo"],
        "session_minutes": 75,
        "intensity": "match_sim",
        "message": "Plan full runouts; practice under shot-clock and scoreboard pressure.",
    },
    RatingBand.PRO: {
        "focus": ["table_speed_adapt", "multi_rail_shape", "safety_exchanges", "mental_game"],
        "session_minutes": 90,
        "intensity": "performance",
        "message": "Performance block: variability training + pressure sets + recovery routine.",
    },
}


def _mental_cues(band: RatingBand) -> list[str]:
    base = [
        "One shot at a time — commit to contact point before stepping in.",
        "If the out is unclear, choose the two-way safety.",
    ]
    if band == RatingBand.BEGINNER:
        return base + ["Slow is smooth; smooth is fast — don't rush the tip."]
    if band == RatingBand.INTERMEDIATE:
        return base + ["Lose the hero pot: leave a lock for later."]
    if band == RatingBand.ADVANCED:
        return base + ["Breathe on every miss; reset PSR fully before the next ball."]
    return base + ["Own the lag: control table speed early in the set."]


def _pre_match(player: PlayerProfile) -> dict[str, Any]:
    return {
        "warmup": [
            "10 soft center-ball stops",
            "10 short follow / draw pairs",
            "5 practice breaks (focus CB box, not power)",
            "2 minutes visualization of first rack out",
        ],
        "checklist": [
            f"Discipline: {player.discipline}",
            f"Table speed noted: {player.table_speed}",
            "Chalk, tip shape, bridge hand dry",
            "Opponent rating awareness — don't overhit early",
        ],
        "open_rack_plan": (
            "Take lag seriously; if break is weak side, play controlled safety early "
            "rather than force a low-percentage out."
            if player.band in (RatingBand.BEGINNER, RatingBand.INTERMEDIATE)
            else "Break to your pattern preference; identify key ball before first offensive shot."
        ),
    }


def _practice_plan(player: PlayerProfile, minutes: int | None = None) -> dict[str, Any]:
    curr = _BAND_CURRICULUM[player.band]
    mins = minutes or curr["session_minutes"]
    weak = [w for w in (player.weaknesses or []) if w]
    focus = list(dict.fromkeys(weak[:3] + curr["focus"]))[:5]

    blocks = []
    # time allocation
    allot = max(10, mins // max(len(focus), 1))
    for i, skill in enumerate(focus):
        blocks.append(
            {
                "order": i + 1,
                "skill": skill,
                "minutes": allot if i < len(focus) - 1 else mins - allot * (len(focus) - 1),
                "drill": _drill_for_skill(skill, player.band),
            }
        )
    return {
        "duration_minutes": mins,
        "intensity": curr["intensity"],
        "band_message": curr["message"],
        "blocks": blocks,
        "cooldown": "5 min soft center-ball pots + routine review journal (3 bullets)",
    }


def _drill_for_skill(skill: str, band: RatingBand) -> str:
    drills = {
        "stance": "Mirror check: feet, chin, eyes on line — 15 setups without shooting.",
        "stroke": "Pendulum feathers ×20; freeze finish 1 second after contact.",
        "stop_shot": "Stop-shot ladder from 1–4 diamonds.",
        "cue_ball_control": "Draw / follow / stun targets to taped zones.",
        "position_play": "3-ball position route with landing circles.",
        "pattern_play": "Open-table out: verbalize full pattern before first shot.",
        "safety_play": "Two-way safety only — score by leave quality.",
        "break": "Break box control; legal + CB in marked zone.",
        "long_potting": "Long rail cuts progressive angles.",
        "kicks": "One-rail natural kicks to center targets.",
        "mental_focus": "PSR under 10s timer on easy balls.",
        "match_pressure": "Race to 3 vs ghost; miss = full re-rack penalty.",
    }
    d = drills.get(skill) or f"Targeted reps on '{skill}' with measurable make %."
    if band == RatingBand.PRO:
        d += " Add variability (speed/cloth) every 5 reps."
    return d


def _pattern_notes(player: PlayerProfile) -> list[str]:
    notes = []
    if "pattern_play" in (player.weaknesses or []):
        notes.append("Prioritize problem-ball first; build pattern backward from the money ball.")
    if "safety_play" in (player.weaknesses or []):
        notes.append("When in doubt: legal hit + distance; avoid pure offensive hope.")
    if player.band == RatingBand.BEGINNER:
        notes.append("Center-ball defaults: stop and soft follow before side english.")
    if player.band in (RatingBand.ADVANCED, RatingBand.PRO):
        notes.append("Track key-ball errors separately from make percentage.")
    if not notes:
        notes.append("Stay on natural shape lines; minimize high-risk cross-table recovery.")
    return notes


def _pyramid_practice(player: PlayerProfile, cfg, minutes: int | None = None) -> dict[str, Any]:
    """Practice plan scaled for 10-ball vs 15-ball Pyramid + skill targets."""
    mins = int(minutes or (50 if cfg.skill_level == "beginner" else 70))
    blocks = [
        {
            "order": 1,
            "skill": "point_counting",
            "minutes": max(8, mins // 6),
            "drill": (
                f"Announce points-needed to {cfg.points_to_win} before every shot; "
                f"1-ball = 11. Rack size {cfg.rack_size}."
            ),
        },
        {
            "order": 2,
            "skill": "cue_ball_control",
            "minutes": max(10, mins // 5),
            "drill": (
                "Stop / soft-follow ladder on American cloth — classical CB discipline."
                if cfg.rack_size == 10
                else "Long-table stun + soft follow zones for multi-ball shape (15-ball depth)."
            ),
        },
        {
            "order": 3,
            "skill": "value_selection",
            "minutes": max(10, mins // 5),
            "drill": (
                "10-ball: route two highest available values without losing CB."
                if cfg.rack_size == 10
                else "15-ball: open traffic then isolate 1-ball (11) and a top number."
            ),
        },
        {
            "order": 4,
            "skill": "safety_classical",
            "minutes": max(8, mins // 6),
            "drill": "Two-way safety when out is <60% — count race before gambling.",
        },
    ]
    if cfg.call_shot in ("optional", "yes"):
        blocks.append(
            {
                "order": 5,
                "skill": "call_shot",
                "minutes": max(8, mins // 6),
                "drill": (
                    "Call ball+pocket every pot (required for pro; optional advanced). "
                    "No call → safety."
                ),
            }
        )
    else:
        blocks.append(
            {
                "order": 5,
                "skill": "intentional_pocket",
                "minutes": max(8, mins // 6),
                "drill": "No call-shot rule — still pick pocket mentally; log accidental slop.",
            }
        )
    # Weakness block
    weak = (player.weaknesses or ["position_play"])[:1]
    blocks.append(
        {
            "order": 6,
            "skill": weak[0],
            "minutes": max(10, mins - sum(b["minutes"] for b in blocks)),
            "drill": _drill_for_skill(weak[0], player.band),
        }
    )
    return {
        "duration_minutes": mins,
        "intensity": f"pyramid_{cfg.skill_level}",
        "band_message": (
            f"Pyramid {cfg.table_size}/{cfg.rack_size}-ball · first to {cfg.points_to_win} · "
            f"rating weight {cfg.rating_weight}× · classical scoring on American table"
        ),
        "blocks": blocks,
        "cooldown": "Journal: points left, 1-ball decisions, CB errors (3 bullets)",
        "pyramid": cfg.to_dict(),
    }


def coach(
    player: PlayerProfile,
    *,
    mode: str = "session",
    goal: str = "",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    mode: session | practice_plan | pre_match | mental | quick_tip | full | pyramid
    """
    payload = payload or {}
    mode = (mode or payload.get("mode") or "session").lower()
    band = player.band
    disc = normalize_discipline(
        payload.get("discipline") or payload.get("game") or player.discipline
    )
    gk = game_knowledge(disc)
    cfg = resolve_pyramid(player=player, payload=payload)
    is_pyramid = disc == "pyramid" or mode == "pyramid" or bool(
        payload.get("pyramid") or str(payload.get("game") or "").lower() in (
            "pyramid", "rackup-pyramid", "rackup_pyramid",
        )
    )
    continuum_band = skill_band_from_rating(player.rating)

    result: dict[str, Any] = {
        "player_id": player.player_id,
        "display_name": player.display_name,
        "rating": player.rating,
        "band": band.value,
        "continuum_band": continuum_band,
        "discipline": disc,
        "discipline_display": gk.get("display"),
        "mode": mode,
        "goal": goal,
        "band_curriculum": _BAND_CURRICULUM[band],
        "game_knowledge": {
            "objective": gk.get("objective"),
            "rack": gk.get("rack"),
            "key_rules": gk.get("key_rules"),
            "good_play": gk.get("good_play"),
            "bad_play": gk.get("bad_play"),
            "coaching_focus": coaching_focus(disc, player.rating),
            "fouls": gk.get("fouls"),
        },
        "pyramid": cfg.to_dict() if is_pyramid else None,
        "ruleset": player.ruleset or payload.get("ruleset") or "",
    }

    if is_pyramid or mode == "pyramid":
        result["classical_mindset"] = classical_mindset_tips(cfg)
        result["race"] = race_context(
            cfg,
            my_score=int(payload.get("my_score", player.pyramid_score) or 0),
            opp_score=int(payload.get("opp_score", player.pyramid_opp_score) or 0),
        )

    if mode in ("session", "full", "practice_plan", "practice", "pyramid"):
        if is_pyramid or mode == "pyramid":
            result["practice_plan"] = _pyramid_practice(
                player, cfg, minutes=payload.get("minutes")
            )
        else:
            result["practice_plan"] = _practice_plan(
                player, minutes=payload.get("minutes")
            )
    if mode in ("session", "full", "pre_match", "prematch", "pyramid"):
        pm = _pre_match(player)
        if is_pyramid:
            pm["pyramid"] = {
                "target": cfg.points_to_win,
                "rack_size": cfg.rack_size,
                "table_size": cfg.table_size,
                "call_shot": cfg.call_shot,
                "open_plan": (
                    "Control break; prioritize table count; never gift the 1-ball (11)."
                ),
            }
            pm["warmup"] = [
                "10 stop-shots (classical CB)",
                f"5 value-routes on {cfg.rack_size}-ball layout",
                "3 safety exchanges scoring leave quality",
                f"Visualize first-to-{cfg.points_to_win} endgame count",
            ]
        result["pre_match"] = pm
    if mode in ("session", "full", "mental", "mental_game", "pyramid"):
        cues = _mental_cues(band)
        if is_pyramid:
            cues = [
                f"Need {cfg.points_to_win - int(payload.get('my_score', player.pyramid_score) or 0)} "
                f"more points — count every ball value (1=11).",
                "American table, classical brain: percentage over highlight pots.",
            ] + cues
        result["mental_game"] = {
            "cues": cues,
            "pressure_protocol": [
                "Box breathe 4-4-4 between games",
                "After miss: chalk + full PSR — never rush the next tip",
                "Between racks: one tactical note only, then reset",
                "Re-state points-needed before breaking",
            ],
        }
    if mode in ("session", "full", "pattern", "quick_tip", "pyramid"):
        notes = _pattern_notes(player)
        if is_pyramid:
            notes = [
                f"{cfg.table_size} → {cfg.rack_size}-ball rack; target {cfg.points_to_win}.",
                "Value density: protect 1-ball (11) and high numbers in traffic.",
            ] + notes
        else:
            notes = list(gk.get("good_play") or [])[:3] + notes
        result["pattern_recognition"] = notes

    from plugins.rackup_coach.games import default_rating_weight

    result["individualization"] = {
        "train_now": (player.weaknesses or [])[:4] or _BAND_CURRICULUM[band]["focus"][:3],
        "protect": (player.strengths or [])[:3],
        "recent_form": _form_summary(player),
        "pyramid_skill": cfg.skill_level if is_pyramid else None,
        "rating_weight": (
            cfg.rating_weight
            if is_pyramid
            else default_rating_weight(disc, skill_level=player.skill_level or "")
        ),
        "discipline": disc,
    }

    if goal:
        result["goal_response"] = _answer_goal(player, goal, cfg=cfg if is_pyramid else None)

    result["next_actions"] = [
        f"Run today's practice plan ({result.get('practice_plan', {}).get('duration_minutes', 45)} min)",
        "Log 3 weaknesses observed after the session",
        "Request shot_of_the_day with discipline=pyramid + table_size",
    ]
    return result


def _form_summary(player: PlayerProfile) -> str:
    res = player.recent_results or []
    if not res:
        return "No recent results supplied — coach using rating band defaults."
    wins = sum(1 for r in res if r.get("won"))
    n = len(res)
    return f"Last {n} scored sessions: {wins}-{n - wins}. Adjust aggression accordingly."


def _answer_goal(player: PlayerProfile, goal: str, cfg=None) -> str:
    g = goal.lower()
    if cfg and ("pyramid" in g or "points" in g or "1-ball" in g or "one ball" in g):
        return (
            f"Pyramid {cfg.table_size}/{cfg.rack_size}-ball: first to {cfg.points_to_win}. "
            f"1-ball=11; call_shot={cfg.call_shot}; weight={cfg.rating_weight}×. "
            "Count before every stroke."
        )
    if "break" in g:
        return "Focus break box control before adding power; film one set of 10 breaks."
    if "nervous" in g or "pressure" in g or "tilt" in g:
        return "Use mental_game pressure protocol; shorten PSR, never skip it."
    if "safety" in g:
        return "Drill two-way safeties; score leave quality, not just legal hits."
    if "fargo" in g or "rating" in g:
        return "Rating rises from consistency: stop/position first, then pattern speed."
    return (
        f"For a {player.band.value} ({player.rating:.0f}) player: "
        f"prioritize {', '.join((player.weaknesses or _BAND_CURRICULUM[player.band]['focus'])[:2])} this week."
    )


def run(player: PlayerProfile, payload: dict[str, Any] | None = None, goal: str = "") -> dict[str, Any]:
    payload = payload or {}
    mode = str(payload.get("mode") or "full")
    if (player.discipline or "").lower() == "pyramid" and mode == "full":
        mode = "pyramid"
    return coach(
        player,
        mode=mode,
        goal=goal or str(payload.get("goal") or ""),
        payload=payload,
    )
