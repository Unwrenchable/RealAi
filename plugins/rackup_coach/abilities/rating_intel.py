"""Dynamic player rating intelligence — ROC Glicko-2 + Pyramid skill metadata."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.glicko2 import (
    DEFAULT_RD,
    DEFAULT_VOL,
    PlayerRating,
    band_for,
    expected_score,
    system_info,
)
from plugins.rackup_coach.leagues import format_rating_chip
from plugins.rackup_coach.pyramid import resolve_pyramid, weighted_rating_delta
from plugins.rackup_coach.types import PlayerProfile, rating_band


def rating_intelligence(
    player: PlayerProfile,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = payload or {}
    history = list(payload.get("rating_history") or [])
    results = player.recent_results or list(payload.get("results") or [])
    cfg = resolve_pyramid(player=player, payload=payload)

    current = float(player.rating or 0)
    rd = float(
        payload.get("rd")
        or getattr(player, "rd", None)
        or DEFAULT_RD
    )
    vol = float(
        payload.get("volatility")
        or getattr(player, "volatility", None)
        or DEFAULT_VOL
    )
    me = PlayerRating(rating=current, rd=rd, volatility=vol, player_id=player.player_id)
    band = rating_band(current).value
    band_label = band_for(current)

    if history:
        ratings = [float(h.get("rating") or h.get("value") or 0) for h in history]
        delta = ratings[-1] - ratings[0] if len(ratings) > 1 else 0.0
        hist_vol = 0.0
        if len(ratings) > 2:
            diffs = [abs(ratings[i] - ratings[i - 1]) for i in range(1, len(ratings))]
            hist_vol = sum(diffs) / len(diffs)
        # Prefer last history RD if present
        last = history[-1] if history else {}
        if last.get("rd") is not None:
            rd = float(last["rd"])
            me.rd = rd
    else:
        delta = 0.0
        hist_vol = 0.0
        ratings = [current]

    wins = sum(1 for r in results if r.get("won"))
    n = len(results) or 0
    win_rate = (wins / n) if n else None

    opp_ratings = [
        float(r.get("opponent_rating") or 0) for r in results if r.get("opponent_rating")
    ]
    avg_opp = sum(opp_ratings) / len(opp_ratings) if opp_ratings else None

    trajectory = "stable"
    if delta > 15:
        trajectory = "climbing"
    elif delta < -15:
        trajectory = "slipping"
    if hist_vol > 25 or vol > 0.08:
        trajectory = "volatile_" + trajectory
    if rd >= 150:
        trajectory = "provisional_" + trajectory.replace("provisional_", "")

    recommendations = []
    if rd >= 150:
        recommendations.append(
            f"High RD ({rd:.0f}): rating is uncertain — more rated singles will tighten the ladder."
        )
    if trajectory.startswith("slipping") or "slipping" in trajectory:
        recommendations.append("Return to fundamentals block (stop/position) for 3 sessions.")
    if "climbing" in trajectory:
        recommendations.append("Schedule one uphill matchup this week to test the new level.")
    if win_rate is not None and win_rate > 0.7 and avg_opp and avg_opp < current - 40:
        recommendations.append("Possible soft schedule — seek closer ratings to validate climb.")
    if win_rate is not None and win_rate < 0.35:
        recommendations.append("Shrink aggression; add safety drills before rating events.")
    recommendations.append(
        f"Pyramid skill={cfg.skill_level}: skill-matrix weight {cfg.rating_weight}× "
        f"({cfg.table_size}/{cfg.rack_size}-ball, first to {cfg.points_to_win}) — "
        f"competitive ladder remains Glicko-2."
    )
    if cfg.rating_weight < 1.0:
        recommendations.append(
            "Lower Pyramid skill weight is coaching metadata — Glicko still moves on every rated match."
        )
    if not any("Maintain" in r for r in recommendations) and rd < 80 and abs(delta) < 10:
        recommendations.append("Maintain current plan; reassess after 5 more rated sessions.")

    raw_last = float(payload.get("last_raw_delta") or delta or 0)
    weighted_last = weighted_rating_delta(raw_last, cfg.skill_level)

    # Expected score vs average opponent if we have one
    exp_vs_field = None
    if avg_opp is not None:
        field = PlayerRating(rating=avg_opp, rd=DEFAULT_RD, volatility=DEFAULT_VOL)
        exp_vs_field = round(expected_score(me, field), 4)

    return {
        "player_id": player.player_id,
        "current_rating": current,
        "rd": rd,
        "volatility": round(vol, 6),
        "rating_chip": format_rating_chip(current),
        "band": band,
        "band_label": band_label,
        "display": me.display,
        "ladder": "roc_glicko2",
        "algorithm": "glicko2_v1",
        "system": system_info(),
        "trajectory": trajectory,
        "delta_window": round(delta, 1),
        "history_volatility": round(hist_vol, 1),
        "glicko_volatility": round(vol, 6),
        "win_rate_recent": win_rate,
        "avg_opponent_rating": avg_opp,
        "expected_score_vs_field": exp_vs_field,
        "sample_size": n,
        "uncertainty": {
            "rd": rd,
            "provisional": rd >= 150,
            "tight": rd <= 50,
            "note": "Matchmaking should widen windows when RD is high",
        },
        "pyramid": cfg.to_dict(),
        "rating_weight": cfg.rating_weight,
        "weighted_delta_example": round(weighted_last, 2),
        "recommendations": recommendations,
        "next_band_distance": _distance_to_next_band(current),
    }


def _distance_to_next_band(rating: float) -> dict[str, Any]:
    """ROC display band thresholds (labels only)."""
    thresholds = [
        (400, "Intermediate"),
        (500, "Advanced"),
        (600, "Expert"),
        (700, "Elite"),
    ]
    for t, name in thresholds:
        if rating < t:
            return {
                "next_threshold": t,
                "next_band_label": name,
                "points_needed": round(t - rating, 1),
            }
    return {"next_threshold": None, "next_band_label": None, "points_needed": 0}


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return rating_intelligence(player, payload)
