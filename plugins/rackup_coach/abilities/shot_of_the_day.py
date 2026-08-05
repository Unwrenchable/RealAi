"""Shot of the Day — useful, rating-aware recommendations (not pure trick shots)."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.types import PlayerProfile, RatingBand, rating_band


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
]


def _score_shot(shot: dict[str, Any], player: PlayerProfile) -> float:
    band = player.band.value
    score = 0.0
    if band in shot.get("bands", []):
        score += 3.0
    # Prefer mid-band fit
    bands = shot.get("bands") or []
    if bands and band == bands[len(bands) // 2]:
        score += 1.0
    disc = player.discipline or "eight_ball"
    if disc in shot.get("discipline", []):
        score += 2.0
    weak = {w.lower() for w in (player.weaknesses or [])}
    for w in shot.get("weaknesses", []):
        if w in weak:
            score += 4.0
    # Recent losses → emphasize fundamentals for lower bands
    losses = sum(1 for r in (player.recent_results or []) if not r.get("won", True))
    if losses >= 2 and band in ("beginner", "intermediate"):
        if "cue_ball_control" in shot.get("weaknesses", []) or "speed_control" in shot.get(
            "weaknesses", []
        ):
            score += 2.0
    # History notes keyword boost
    notes = " ".join(player.history_notes or []).lower()
    for w in shot.get("weaknesses", []):
        if w.replace("_", " ") in notes:
            score += 1.5
    return score


def recommend_shot_of_the_day(
    player: PlayerProfile,
    *,
    seed_hint: str = "",
    count: int = 1,
) -> dict[str, Any]:
    """Return 1+ practical shots ranked for this player."""
    ranked = sorted(_SHOT_LIBRARY, key=lambda s: _score_shot(s, player), reverse=True)
    if seed_hint:
        hint = seed_hint.lower()
        hinted = [s for s in ranked if hint in s["title"].lower() or hint in s["id"]]
        if hinted:
            ranked = hinted + [s for s in ranked if s not in hinted]

    picks = ranked[: max(1, min(count, 5))]
    primary = picks[0]
    band = player.band.value

    coaching_line = {
        RatingBand.BEGINNER: "Keep it simple today — own the fundamentals.",
        RatingBand.INTERMEDIATE: "Link cue-ball control to a real out pattern.",
        RatingBand.ADVANCED: "Demand shape windows, not just pots.",
        RatingBand.PRO: "Pressure-test the shot under match tempo.",
    }[player.band]

    return {
        "date_role": "shot_of_the_day",
        "player_id": player.player_id,
        "rating": player.rating,
        "band": band,
        "discipline": player.discipline,
        "coaching_line": coaching_line,
        "primary": {
            "id": primary["id"],
            "title": primary["title"],
            "setup": primary["setup"],
            "objective": primary["objective"],
            "why_this_shot": primary["why"],
            "targets_weaknesses": primary["weaknesses"],
            "reps": primary["reps"],
            "success_metric": primary["success_metric"],
            "pro_tip": primary["pro_tip"],
            "not_a_trick_shot": True,
        },
        "alternates": [
            {
                "id": s["id"],
                "title": s["title"],
                "targets_weaknesses": s["weaknesses"],
                "reps": s["reps"],
            }
            for s in picks[1:]
        ],
        "personalization": {
            "weaknesses_used": player.weaknesses,
            "strengths_noted": player.strengths,
            "recent_results_count": len(player.recent_results or []),
            "table_speed": player.table_speed,
        },
    }


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    return recommend_shot_of_the_day(
        player,
        seed_hint=str(payload.get("hint") or payload.get("focus") or ""),
        count=int(payload.get("count") or 1),
    )
