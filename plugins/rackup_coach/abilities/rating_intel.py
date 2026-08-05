"""Dynamic player rating intelligence (includes Pyramid skill weights)."""
from __future__ import annotations

from typing import Any

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
    band = rating_band(current).value

    if history:
        ratings = [float(h.get("rating") or h.get("value") or 0) for h in history]
        delta = ratings[-1] - ratings[0] if len(ratings) > 1 else 0.0
        volatility = 0.0
        if len(ratings) > 2:
            diffs = [abs(ratings[i] - ratings[i - 1]) for i in range(1, len(ratings))]
            volatility = sum(diffs) / len(diffs)
    else:
        delta = 0.0
        volatility = 0.0
        ratings = [current]

    wins = sum(1 for r in results if r.get("won"))
    n = len(results) or 0
    win_rate = (wins / n) if n else None

    # Expected score vs field average if provided
    opp_ratings = [float(r.get("opponent_rating") or 0) for r in results if r.get("opponent_rating")]
    avg_opp = sum(opp_ratings) / len(opp_ratings) if opp_ratings else None

    trajectory = "stable"
    if delta > 25:
        trajectory = "climbing"
    elif delta < -25:
        trajectory = "slipping"
    if volatility > 40:
        trajectory = "volatile_" + trajectory

    recommendations = []
    if trajectory.startswith("slipping"):
        recommendations.append("Return to fundamentals block (stop/position) for 3 sessions.")
    if trajectory.startswith("climbing"):
        recommendations.append("Schedule one uphill matchup this week to test the new level.")
    if win_rate is not None and win_rate > 0.7 and avg_opp and avg_opp < current - 40:
        recommendations.append("Possible soft schedule — seek closer ratings to validate climb.")
    if win_rate is not None and win_rate < 0.35:
        recommendations.append("Shrink aggression; add safety drills before rating events.")
    recommendations.append(
        f"Pyramid skill={cfg.skill_level}: rating moves weight {cfg.rating_weight}× "
        f"({cfg.table_size}/{cfg.rack_size}-ball, first to {cfg.points_to_win})."
    )
    if cfg.rating_weight < 1.0:
        recommendations.append(
            "Lower skill weight means smaller rating swings — focus on consistency vs spikes."
        )
    if cfg.rating_weight > 1.0:
        recommendations.append(
            "Pro weight amplifies rating swings — avoid soft schedules and tilt losses."
        )
    if not recommendations:
        recommendations.append("Maintain current plan; reassess after 5 more rated sessions.")

    # Example weighted delta if host sent last raw delta
    raw_last = float(payload.get("last_raw_delta") or delta or 0)
    weighted_last = weighted_rating_delta(raw_last, cfg.skill_level)

    return {
        "player_id": player.player_id,
        "current_rating": current,
        "band": band,
        "trajectory": trajectory,
        "delta_window": round(delta, 1),
        "volatility": round(volatility, 1),
        "win_rate_recent": win_rate,
        "avg_opponent_rating": avg_opp,
        "sample_size": n,
        "pyramid": cfg.to_dict(),
        "rating_weight": cfg.rating_weight,
        "weighted_delta_example": round(weighted_last, 2),
        "recommendations": recommendations,
        "next_band_distance": _distance_to_next_band(current),
    }


def _distance_to_next_band(rating: float) -> dict[str, Any]:
    thresholds = [400, 700, 900, 1200]
    for t in thresholds:
        if rating < t:
            return {"next_threshold": t, "points_needed": round(t - rating, 1)}
    return {"next_threshold": None, "points_needed": 0}


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return rating_intelligence(player, payload)
