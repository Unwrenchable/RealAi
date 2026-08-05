"""Post-match skill / rating calculation (RealAI owns the algorithm)."""
from __future__ import annotations

import math
from typing import Any

from plugins.rackup_coach.pyramid import resolve_pyramid, weighted_rating_delta
from plugins.rackup_coach.types import PlayerProfile, rating_band


def _expected_score(rating: float, opp_rating: float) -> float:
    """Logistic expected score in [0,1] (Elo-style)."""
    return 1.0 / (1.0 + math.pow(10.0, (opp_rating - rating) / 400.0))


def compute_rating_update(
    player: PlayerProfile,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    RackUp sends match result; RealAI returns new rating + skill signals.

    Required payload:
      opponent_rating: number
      won: bool  OR  score / opp_score for Pyramid point races
    Optional:
      k_factor, discipline, table_size, skill_level, margin, forfeit, provisional
    """
    payload = payload or {}
    cfg = resolve_pyramid(player=player, payload=payload)
    rating = float(player.rating or 500.0)
    opp = float(payload.get("opponent_rating") or payload.get("opp_rating") or rating)
    k = float(payload.get("k_factor") or (32 if rating < 700 else 24))

    # Outcome 1.0 win / 0.0 loss / 0.5 draw
    if "won" in payload:
        outcome = 1.0 if payload.get("won") else 0.0
        if payload.get("draw") or payload.get("tie"):
            outcome = 0.5
    elif "my_score" in payload and "opp_score" in payload:
        ms, os_ = int(payload["my_score"]), int(payload["opp_score"])
        target = int(payload.get("points_to_win") or cfg.points_to_win)
        # Prefer who hit target; else higher score
        if ms >= target and os_ < target:
            outcome = 1.0
        elif os_ >= target and ms < target:
            outcome = 0.0
        elif ms == os_:
            outcome = 0.5
        else:
            outcome = 1.0 if ms > os_ else 0.0
    else:
        return {
            "error": "missing_outcome",
            "hint": "Provide won:bool or my_score+opp_score",
        }

    expected = _expected_score(rating, opp)
    raw_delta = k * (outcome - expected)

    # Margin dampener (optional)
    margin = payload.get("margin")
    if margin is not None:
        try:
            m = abs(float(margin))
            raw_delta *= min(1.25, 1.0 + m / 100.0)
        except (TypeError, ValueError):
            pass
    if payload.get("forfeit"):
        raw_delta *= 0.5

    # Pyramid skill weight
    weight = float(cfg.rating_weight)
    if (player.discipline or "").lower() == "pyramid" or payload.get("game") == "pyramid":
        weighted = weighted_rating_delta(raw_delta, cfg.skill_level)
    else:
        # Still allow skill_level weight when provided
        weighted = raw_delta * weight if payload.get("skill_level") or player.skill_level else raw_delta

    if payload.get("provisional"):
        weighted *= 1.5  # faster movement for new players

    new_rating = max(100.0, rating + weighted)
    old_band = rating_band(rating).value
    new_band = rating_band(new_rating).value

    return {
        "player_id": player.player_id,
        "algorithm": "elo_logistic_v1",
        "discipline": player.discipline or payload.get("discipline") or "pyramid",
        "pyramid": cfg.to_dict(),
        "input": {
            "rating_before": rating,
            "opponent_rating": opp,
            "outcome": outcome,
            "expected": round(expected, 4),
            "k_factor": k,
            "rating_weight": weight,
        },
        "raw_delta": round(raw_delta, 3),
        "weighted_delta": round(weighted, 3),
        "rating_after": round(new_rating, 2),
        "band_before": old_band,
        "band_after": new_band,
        "band_changed": old_band != new_band,
        "skill_signals": {
            "suggested_skill_level": cfg.skill_level,
            "points_to_win_next": cfg.points_to_win,
            "table_size": cfg.table_size,
            "rack_size": cfg.rack_size,
        },
        "persist_hint": {
            "fields_to_write": ["rating", "rating_updated_at", "last_match_delta"],
            "owner": "RackUp DB — RealAI does not persist ratings",
        },
    }


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return compute_rating_update(player, payload)
