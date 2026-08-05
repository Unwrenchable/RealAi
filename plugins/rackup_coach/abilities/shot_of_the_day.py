"""Shot of the Day — useful, rating-aware recommendations (not pure trick shots).

Includes RackUp Pyramid variants for 7ft/10-ball and 9ft/15-ball racks.
"""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.pyramid import classical_mindset_tips, resolve_pyramid
from plugins.rackup_coach.types import PlayerProfile, RatingBand


# Catalog: practical shots keyed by weakness + rating appropriateness
_SHOT_LIBRARY: list[dict[str, Any]] = [
    {
        "id": "stop-shot-ladder",
        "title": "Stop-shot ladder (cue ball freezes)",
        "weaknesses": ["cue_ball_control", "position_play", "speed_control"],
        "bands": ["beginner", "intermediate"],
        "discipline": ["eight_ball", "nine_ball", "ten_ball", "straight_pool"],
        "setup": "Object ball on foot spot; CB one diamond back on center line.",
        "objective": "Pot center and kill CB dead for stop; then increase distance.",
        "why": "Stop shots are the foundation of pattern play and shape.",
        "reps": 30,
        "success_metric": "20/30 stop within a half-ball of original CB line",
        "pro_tip": "Tip center, level cue, accelerate through — don't jab.",
    },
    {
        "id": "draw-length-control",
        "title": "Measured draw to the rail",
        "weaknesses": ["cue_ball_control", "english", "position_play"],
        "bands": ["beginner", "intermediate", "advanced"],
        "discipline": ["eight_ball", "nine_ball", "ten_ball"],
        "setup": "Straight-in mid-table; targets for CB draw of 1, 2, 3 diamonds.",
        "objective": "Same stroke family; only tip placement/speed change draw length.",
        "why": "Uncontrolled draw is the #1 shape killer below advanced level.",
        "reps": 24,
        "success_metric": "Hit distance window 16/24",
        "pro_tip": "Low tip + smooth follow-through; avoid scooping.",
    },
    {
        "id": "soft-follow-chain",
        "title": "Soft follow for natural shape",
        "weaknesses": ["position_play", "speed_control", "pattern_play"],
        "bands": ["beginner", "intermediate"],
        "discipline": ["eight_ball", "nine_ball"],
        "setup": "Three-ball line; pot first with soft follow into second line.",
        "objective": "Leave CB in a 6-inch landing zone for next ball.",
        "why": "Soft follow is more reliable than stun+english for beginners.",
        "reps": 20,
        "success_metric": "Landing zone 14/20",
        "pro_tip": "Tip slightly above center; think 'roll', not 'hit'.",
    },
    {
        "id": "rail-cut-thin",
        "title": "Thin rail cuts (contact point discipline)",
        "weaknesses": ["rail_shots", "long_potting", "stance"],
        "bands": ["intermediate", "advanced", "pro"],
        "discipline": ["eight_ball", "nine_ball", "ten_ball", "one_pocket"],
        "setup": "Object ball frozen or near rail; progressive cut angles 15°–45°.",
        "objective": "Call contact point; no rail-first guesses.",
        "why": "Rail cuts expose aim and cue elevation issues under match pressure.",
        "reps": 25,
        "success_metric": "Pocket 18/25 at intermediate; 21/25 advanced+",
        "pro_tip": "Short bridge, still lower body; aim edge of CB to contact point.",
    },
    {
        "id": "break-box-control",
        "title": "Break box & second-ball control",
        "weaknesses": ["break", "speed_control", "cue_ball_control"],
        "bands": ["intermediate", "advanced", "pro"],
        "discipline": ["eight_ball", "nine_ball", "ten_ball"],
        "setup": "Rack tight; mark a CB landing box after break (center or side).",
        "objective": "Legal break + CB in box without scratching.",
        "why": "Break consistency separates intermediate from advanced league players.",
        "reps": 15,
        "success_metric": "CB in box 10/15; no scratch",
        "pro_tip": "Stance wider, grip loose; hit through center — power from legs.",
    },
    {
        "id": "safety-two-way",
        "title": "Two-way safety (escape + cover)",
        "weaknesses": ["safety_play", "pattern_play", "mental_focus"],
        "bands": ["intermediate", "advanced", "pro"],
        "discipline": ["eight_ball", "straight_pool", "one_pocket"],
        "setup": "Clustered remaining balls; legal hit with snooker-quality leave.",
        "objective": "Hit legal ball and leave opponent snookered or poor angle.",
        "why": "Winning frames often come from safeties, not hero pots.",
        "reps": 12,
        "success_metric": "Opponent needs kick/bank to hit 8/12",
        "pro_tip": "Plan the out if they miss; never pure 'hit and hope'.",
    },
    {
        "id": "long-rail-stun",
        "title": "Long-table stun for shape",
        "weaknesses": ["long_potting", "cue_ball_control", "position_play"],
        "bands": ["advanced", "pro"],
        "discipline": ["nine_ball", "ten_ball", "straight_pool"],
        "setup": "Diagonal long pot; stun to hold or slide half diamond.",
        "objective": "Pot + CB travel within a diamond of planned line.",
        "why": "Long stun control is pro-level pattern currency.",
        "reps": 20,
        "success_metric": "16/20 pots; 12/20 shape windows",
        "pro_tip": "Center tip, firm stroke; pause at address to kill steering.",
    },
    {
        "id": "kick-one-rail",
        "title": "One-rail natural kicks",
        "weaknesses": ["kicks", "banks", "table_speed_adapt"],
        "bands": ["intermediate", "advanced", "pro"],
        "discipline": ["nine_ball", "ten_ball", "one_pocket"],
        "setup": "CB frozen short rail; object mid long rail — natural track kick.",
        "objective": "Contact object ball legally with planned speed.",
        "why": "Kick skill recovers innings after a poor leave.",
        "reps": 18,
        "success_metric": "Legal contact 14/18",
        "pro_tip": "Mirror systems first; then adjust for cloth speed.",
    },
    {
        "id": "pre-shot-routine",
        "title": "Pre-shot routine under clock",
        "weaknesses": ["pre_shot_routine", "mental_focus", "match_pressure", "stroke"],
        "bands": ["beginner", "intermediate", "advanced", "pro"],
        "discipline": ["eight_ball", "nine_ball", "ten_ball", "straight_pool"],
        "setup": "Any easy straight-ins; enforce 8–12s PSR every shot.",
        "objective": "Same walk-in, chalk, aim, feather, fire — no rush.",
        "why": "Under pressure, routine is the skill that fails first.",
        "reps": 20,
        "success_metric": "20 consecutive shots with unbroken routine",
        "pro_tip": "If interrupted, step away and restart PSR fully.",
    },
    {
        "id": "pattern-eight-out",
        "title": "Eight-ball out-pattern from open table",
        "weaknesses": ["pattern_play", "position_play", "safety_play"],
        "bands": ["intermediate", "advanced", "pro"],
        "discipline": ["eight_ball"],
        "setup": "Open table, 4–5 of your balls + 8; plan full runout before shooting.",
        "objective": "Verbalize order, key shape ball, and bail-out safety.",
        "why": "Pros decide the out before the first tip; amateurs chase balls.",
        "reps": 10,
        "success_metric": "Clear plan + successful out or smart safety 7/10",
        "pro_tip": "Identify problem ball first; build the pattern backward from the 8.",
    },
    # --- RackUp Pyramid (classical points on American tables) ---
    {
        "id": "pyramid-1ball-premium",
        "title": "Pyramid: protect & take the 1-ball (11 pts)",
        "weaknesses": ["pattern_play", "safety_play", "cue_ball_control", "mental_focus"],
        "bands": ["beginner", "intermediate", "advanced", "pro"],
        "discipline": ["pyramid", "straight_pool"],
        "pyramid_rack": [10, 15],
        "setup": "1-ball mid-table with traffic; practice legal approach + CB shape after.",
        "objective": "Either bury opponent from the 1 or pot 1 when percentage ≥70%.",
        "why": "In Pyramid the 1-ball is worth 11 — largest single classical swing.",
        "reps": 16,
        "success_metric": "12/16: either safe bury or clean pot with shape",
        "pro_tip": "Count points before touching the 1; never gift 11.",
    },
    {
        "id": "pyramid-10ball-value-route",
        "title": "Pyramid 7ft/10-ball: high-value two-ball route",
        "weaknesses": ["pattern_play", "position_play", "speed_control"],
        "bands": ["beginner", "intermediate", "advanced", "pro"],
        "discipline": ["pyramid"],
        "pyramid_rack": [10],
        "setup": "10-ball rack open; identify next 2 highest available values + shape link.",
        "objective": "Pot value sequence without losing CB; track score to skill target.",
        "why": "10-ball Pyramid has fewer objects — each ball is a larger share of race points.",
        "reps": 12,
        "success_metric": "Score ≥ half of points-to-win in a controlled drill set",
        "pro_tip": "On 7ft, prefer stop/soft-follow chains over multi-rail recovery.",
    },
    {
        "id": "pyramid-15ball-number-ladder",
        "title": "Pyramid 9ft/15-ball: number ladder (low risk → high value)",
        "weaknesses": ["pattern_play", "long_potting", "position_play"],
        "bands": ["intermediate", "advanced", "pro"],
        "discipline": ["pyramid"],
        "pyramid_rack": [15],
        "setup": "Scattered 15-ball set; build a ladder that finishes on 1-ball (11) or 15.",
        "objective": "Verbalize full point path before first tip; execute or two-way safe.",
        "why": "15-ball Pyramid rewards classical pattern depth on a full American table.",
        "reps": 10,
        "success_metric": "7/10 plans hold without emergency hero pots",
        "pro_tip": "Open traffic early; save premium numbers for key innings.",
    },
    {
        "id": "pyramid-call-shot-discipline",
        "title": "Pyramid call-shot discipline (advanced/pro)",
        "weaknesses": ["pre_shot_routine", "mental_focus", "long_potting"],
        "bands": ["advanced", "pro"],
        "discipline": ["pyramid"],
        "pyramid_rack": [10, 15],
        "setup": "Any open balls; call ball+pocket every shot (even if skill allows optional).",
        "objective": "Zero slop; if not makeable as called, safety instead.",
        "why": "Pro Pyramid requires call-shot; advanced should train it early.",
        "reps": 20,
        "success_metric": "20 consecutive legal called shots or safeties",
        "pro_tip": "Call early in PSR — don't invent the pocket at tip time.",
    },
    {
        "id": "pyramid-endgame-count",
        "title": "Pyramid endgame point-count drills",
        "weaknesses": ["mental_focus", "pattern_play", "match_pressure"],
        "bands": ["beginner", "intermediate", "advanced", "pro"],
        "discipline": ["pyramid"],
        "pyramid_rack": [10, 15],
        "setup": "Start mid-score (e.g. need 12–18 pts); play out with full classical counting.",
        "objective": "Know points needed before every stroke; never chase dead balls.",
        "why": "First-to-target races are lost by players who stop counting.",
        "reps": 8,
        "success_metric": "Correct points-needed stated before each of 8 racks",
        "pro_tip": "Announce 'need X' out loud during practice.",
    },
]


def _score_shot(
    shot: dict[str, Any],
    player: PlayerProfile,
    *,
    pyramid: dict[str, Any] | None = None,
) -> float:
    band = player.band.value
    score = 0.0
    if band in shot.get("bands", []):
        score += 3.0
    bands = shot.get("bands") or []
    if bands and band == bands[len(bands) // 2]:
        score += 1.0
    disc = (player.discipline or "eight_ball").lower()
    if disc in shot.get("discipline", []):
        score += 2.0
    weak = {w.lower() for w in (player.weaknesses or [])}
    for w in shot.get("weaknesses", []):
        if w in weak:
            score += 4.0
    losses = sum(1 for r in (player.recent_results or []) if not r.get("won", True))
    if losses >= 2 and band in ("beginner", "intermediate"):
        if "cue_ball_control" in shot.get("weaknesses", []) or "speed_control" in shot.get(
            "weaknesses", []
        ):
            score += 2.0
    notes = " ".join(player.history_notes or []).lower()
    for w in shot.get("weaknesses", []):
        if w.replace("_", " ") in notes:
            score += 1.5

    # Pyramid boosts
    if pyramid:
        rack = int(pyramid.get("rack_size") or 15)
        skill = str(pyramid.get("skill_level") or band)
        if "pyramid" in shot.get("discipline", []):
            score += 5.0
            allowed = shot.get("pyramid_rack") or [10, 15]
            if rack in allowed:
                score += 4.0
            else:
                score -= 8.0  # wrong rack size variant
            if skill in shot.get("bands", []):
                score += 2.0
        elif disc == "pyramid" and "pyramid" not in shot.get("discipline", []):
            # Prefer pyramid-tagged when playing Pyramid
            score -= 1.0
    return score


def recommend_shot_of_the_day(
    player: PlayerProfile,
    *,
    seed_hint: str = "",
    count: int = 1,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return 1+ practical shots ranked for this player (Pyramid-aware)."""
    payload = payload or {}
    cfg = resolve_pyramid(player=player, payload=payload)
    pyr = cfg.to_dict()
    is_pyramid = (player.discipline or "").lower() == "pyramid" or bool(
        payload.get("pyramid") or payload.get("game") == "pyramid"
    )

    # Merge static + grown library
    try:
        from plugins.rackup_coach.sotd_library import (
            load_grown_shots,
            recently_shown,
            record_shown,
            variety_penalty,
            growth_policy,
        )
        grown = load_grown_shots()
        host_shown = list(payload.get("shown_shot_ids") or [])
        recent = host_shown or recently_shown(player.player_id, limit=14)
    except Exception:
        grown = []
        recent = list(payload.get("shown_shot_ids") or [])
        growth_policy = lambda: {}  # type: ignore
        record_shown = None  # type: ignore
        variety_penalty = lambda sid, r: 0.0  # type: ignore

    library = list(_SHOT_LIBRARY) + [
        g for g in grown if isinstance(g, dict) and g.get("id") and g.get("title")
    ]

    def total_score(s: dict[str, Any]) -> float:
        base = _score_shot(s, player, pyramid=pyr if is_pyramid else None)
        base -= variety_penalty(str(s.get("id") or ""), recent)
        return base

    ranked = sorted(library, key=total_score, reverse=True)
    if is_pyramid:
        ranked = sorted(
            ranked,
            key=lambda s: (
                0 if "pyramid" in s.get("discipline", []) else 1,
                -total_score(s),
            ),
        )
    if seed_hint:
        hint = seed_hint.lower()
        hinted = [s for s in ranked if hint in s["title"].lower() or hint in s["id"]]
        if hinted:
            ranked = hinted + [s for s in ranked if s not in hinted]

    picks = ranked[: max(1, min(count, 5))]
    primary = picks[0]
    band = player.band.value
    # Persist variety (provider-local); RackUp should also store shown IDs
    if record_shown and primary.get("id"):
        try:
            record_shown(
                player.player_id,
                str(primary["id"]),
                meta={"table_size": cfg.table_size, "skill": cfg.skill_level},
            )
        except Exception:
            pass

    coaching_line = {
        RatingBand.BEGINNER: "Keep it simple today — own the fundamentals.",
        RatingBand.INTERMEDIATE: "Link cue-ball control to a real out pattern.",
        RatingBand.ADVANCED: "Demand shape windows, not just pots.",
        RatingBand.PRO: "Pressure-test the shot under match tempo.",
    }[player.band]
    if is_pyramid:
        coaching_line = (
            f"Pyramid {cfg.table_size}/{cfg.rack_size}-ball · "
            f"first to {cfg.points_to_win} · call_shot={cfg.call_shot}. "
            f"{coaching_line} Count points; 1-ball = 11."
        )

    primary_out = {
        "id": primary["id"],
        "title": primary["title"],
        "setup": primary.get("setup"),
        "objective": primary.get("objective"),
        "why_this_shot": primary.get("why"),
        "why_helps_regular_play": primary.get("why")
        or "Builds transferable skills for regular match play (not a trick shot).",
        "targets_weaknesses": primary.get("weaknesses"),
        "reps": primary.get("reps"),
        "success_metric": primary.get("success_metric"),
        "pro_tip": primary.get("pro_tip"),
        "not_a_trick_shot": True,
        "pyramid_rack": primary.get("pyramid_rack"),
    }

    return {
        "date_role": "shot_of_the_day",
        "player_id": player.player_id,
        "rating": player.rating,
        "band": band,
        "discipline": player.discipline,
        "coaching_line": coaching_line,
        "pyramid": pyr if is_pyramid else None,
        "classical_mindset": classical_mindset_tips(cfg) if is_pyramid else [],
        "primary": primary_out,
        "alternates": [
            {
                "id": s["id"],
                "title": s["title"],
                "targets_weaknesses": s.get("weaknesses"),
                "reps": s.get("reps"),
                "pyramid_rack": s.get("pyramid_rack"),
                "why_helps_regular_play": s.get("why"),
            }
            for s in picks[1:]
        ],
        "personalization": {
            "weaknesses_used": player.weaknesses,
            "strengths_noted": player.strengths,
            "recent_results_count": len(player.recent_results or []),
            "table_speed": player.table_speed,
            "table_size": cfg.table_size,
            "rack_size": cfg.rack_size,
            "points_to_win": cfg.points_to_win,
            "skill_level": cfg.skill_level,
            "avoided_recent_ids": recent[:14],
        },
        "variety": {
            "policy": growth_policy() if callable(growth_policy) else growth_policy,
            "library_size_static": len(_SHOT_LIBRARY),
            "library_size_grown": len(grown) if isinstance(grown, list) else 0,
        },
    }


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    return recommend_shot_of_the_day(
        player,
        seed_hint=str(payload.get("hint") or payload.get("focus") or ""),
        count=int(payload.get("count") or 1),
        payload=payload,
    )
