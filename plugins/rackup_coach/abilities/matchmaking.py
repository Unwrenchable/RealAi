"""Smart matchmaking support — style + rating intelligence (no DB)."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.types import PlayerProfile


def matchmaking_advice(
    player: PlayerProfile,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Host supplies candidate opponents:
      candidates: [{player_id, rating, style?, win_rate?, aggression?}, ...]
    """
    payload = payload or {}
    candidates = list(payload.get("candidates") or [])
    pr = float(player.rating or 500)
    # Ideal window widens with uncertainty
    window = float(payload.get("window") or (80 if pr < 700 else 60))

    scored = []
    for c in candidates:
        cr = float(c.get("rating") or 0)
        delta = abs(cr - pr)
        style = str(c.get("style") or "balanced")
        score = max(0.0, 100.0 - delta)
        # Prefer slight uphill for growth if player winning lately
        wins = sum(1 for r in (player.recent_results or []) if r.get("won"))
        losses = len(player.recent_results or []) - wins
        if wins > losses and cr > pr:
            score += 8
        if losses > wins and cr < pr:
            score += 8  # rebuild confidence
        if delta <= window:
            score += 15
        scored.append(
            {
                **c,
                "rating_delta": round(cr - pr, 1),
                "fit_score": round(score, 1),
                "in_window": delta <= window,
                "notes": _notes(player, cr, style),
            }
        )
    scored.sort(key=lambda x: x["fit_score"], reverse=True)

    return {
        "player_id": player.player_id,
        "player_rating": pr,
        "band": player.band.value,
        "recommended_window": [-window, window],
        "ranked_candidates": scored[:20],
        "best": scored[0] if scored else None,
        "policy": {
            "avoid_mismatches_over": window * 2,
            "prefer_same_discipline": player.discipline,
        },
    }


def _notes(player: PlayerProfile, opp_rating: float, style: str) -> str:
    d = opp_rating - player.rating
    if abs(d) <= 25:
        return f"Mirror match ({style}) — ideal skill test."
    if d > 50:
        return "Uphill: play patient safeties; don't force early outs."
    if d < -50:
        return "Downhill: stay disciplined; no exhibition mistakes."
    return f"Competitive window; watch {style} tendencies."


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return matchmaking_advice(player, payload)
