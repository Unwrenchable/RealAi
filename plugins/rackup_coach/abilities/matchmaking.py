"""Smart matchmaking support — style + rating intelligence (no DB)."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.pyramid import resolve_pyramid, weighted_rating_delta
from plugins.rackup_coach.types import PlayerProfile


def matchmaking_advice(
    player: PlayerProfile,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Host supplies candidate opponents:
      candidates: [{player_id, rating, style?, win_rate?, aggression?, skill_level?, table_size?}, ...]
    Pyramid: prefer same table_size/rack + skill band; rating deltas use skill weight.
    """
    payload = payload or {}
    candidates = list(payload.get("candidates") or [])
    pr = float(player.rating or 500)
    cfg = resolve_pyramid(player=player, payload=payload)
    window = float(payload.get("window") or (80 if pr < 700 else 60))
    # Tighter window when pro weight amplifies rating moves
    window = window / max(cfg.rating_weight, 0.5)

    scored = []
    for c in candidates:
        cr = float(c.get("rating") or 0)
        raw_delta = cr - pr
        w_delta = weighted_rating_delta(raw_delta, cfg.skill_level)
        delta = abs(raw_delta)
        style = str(c.get("style") or "balanced")
        score = max(0.0, 100.0 - delta)
        wins = sum(1 for r in (player.recent_results or []) if r.get("won"))
        losses = len(player.recent_results or []) - wins
        if wins > losses and cr > pr:
            score += 8
        if losses > wins and cr < pr:
            score += 8
        if delta <= window:
            score += 15
        # Same Pyramid table / skill preferred
        c_table = str(c.get("table_size") or "")
        c_skill = str(c.get("skill_level") or c.get("pyramid_skill") or "")
        if c_table and resolve_pyramid(table_size=c_table).table_size == cfg.table_size:
            score += 12
        if c_skill and c_skill.lower() == cfg.skill_level:
            score += 10
        elif c_skill:
            score -= 5
        scored.append(
            {
                **c,
                "rating_delta": round(raw_delta, 1),
                "weighted_rating_delta": round(w_delta, 1),
                "rating_weight_applied": cfg.rating_weight,
                "fit_score": round(score, 1),
                "in_window": delta <= window,
                "notes": _notes(player, cr, style, cfg=cfg),
            }
        )
    scored.sort(key=lambda x: x["fit_score"], reverse=True)

    return {
        "player_id": player.player_id,
        "player_rating": pr,
        "band": player.band.value,
        "pyramid": cfg.to_dict(),
        "recommended_window": [-window, window],
        "ranked_candidates": scored[:20],
        "best": scored[0] if scored else None,
        "policy": {
            "avoid_mismatches_over": window * 2,
            "prefer_same_discipline": player.discipline or "pyramid",
            "prefer_same_table_size": cfg.table_size,
            "prefer_same_skill_level": cfg.skill_level,
            "points_to_win": cfg.points_to_win,
            "rating_weight": cfg.rating_weight,
        },
    }


def _notes(player: PlayerProfile, opp_rating: float, style: str, cfg=None) -> str:
    d = opp_rating - player.rating
    base = ""
    if abs(d) <= 25:
        base = f"Mirror match ({style}) — ideal skill test."
    elif d > 50:
        base = "Uphill: play patient safeties; don't force early outs."
    elif d < -50:
        base = "Downhill: stay disciplined; no exhibition mistakes."
    else:
        base = f"Competitive window; watch {style} tendencies."
    if cfg:
        base += (
            f" Pyramid {cfg.table_size}/{cfg.rack_size}-ball to {cfg.points_to_win} "
            f"(weight {cfg.rating_weight}×)."
        )
    return base


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return matchmaking_advice(player, payload)
