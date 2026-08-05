"""Smart matchmaking support — style + rating intelligence (no DB)."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.games import normalize_discipline
from plugins.rackup_coach.leagues import resolve_effective_rating
from plugins.rackup_coach.pyramid import resolve_pyramid, weighted_rating_delta
from plugins.rackup_coach.types import PlayerProfile


def _candidate_rating(c: dict[str, Any]) -> tuple[float, str]:
    """Return (rackup_equiv, source) for a candidate, converting leagues if needed."""
    if c.get("rating") is not None:
        try:
            return float(c["rating"]), "rackup"
        except (TypeError, ValueError):
            pass
    if c.get("league_ratings"):
        eff = resolve_effective_rating(
            {
                "rating": c.get("rating"),
                "league_ratings": c.get("league_ratings"),
                "league_ratings_meta": c.get("league_ratings_meta") or {},
                "primary_rating_system": c.get("primary_rating_system") or "",
                "matches_played_rackup": int(c.get("matches_played_rackup") or 0),
            }
        )
        return float(eff["rating"]), str(eff.get("source") or "league")
    return 500.0, "default_seed"


def matchmaking_advice(
    player: PlayerProfile,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Host supplies candidate opponents (pre-filtered). RealAI ranks only.
    Supports mixed APA/BCA/TAP/VNEA via conversion to shared RackUp scale.
    """
    payload = payload or {}
    candidates = list(payload.get("candidates") or [])
    eff = resolve_effective_rating(player)
    pr = float(eff["rating"])
    disc = normalize_discipline(
        payload.get("discipline") or payload.get("game") or player.discipline
    )
    cfg = resolve_pyramid(player=player, payload=payload)
    weight = float(cfg.rating_weight) if disc == "pyramid" else 1.0
    window = float(payload.get("window") or (80 if pr < 900 else 70))
    window = window / max(weight if disc == "pyramid" else 1.0, 0.5)

    prefs = dict(payload.get("preferences") or {})
    scored = []
    for c in candidates:
        cr, csrc = _candidate_rating(c)
        raw_delta = cr - pr
        w_delta = (
            weighted_rating_delta(raw_delta, cfg.skill_level)
            if disc == "pyramid"
            else raw_delta * weight
        )
        delta = abs(raw_delta)
        style = str(c.get("style") or "balanced")
        score = max(0.0, 100.0 - (delta / max(window, 1)) * 50)
        wins = sum(1 for r in (player.recent_results or []) if r.get("won"))
        losses = len(player.recent_results or []) - wins
        if wins > losses and cr > pr:
            score += 8
        if losses > wins and cr < pr:
            score += 8
        if delta <= window:
            score += 15
        c_table = str(c.get("table_size") or "")
        c_skill = str(c.get("skill_level") or c.get("pyramid_skill") or "")
        c_disc = normalize_discipline(c.get("discipline") or c.get("game") or disc)
        if c_disc == disc:
            score += 8
        if disc == "pyramid":
            if c_table and resolve_pyramid(table_size=c_table).table_size == cfg.table_size:
                score += 12
            if c_skill and c_skill.lower() == cfg.skill_level:
                score += 10
            elif c_skill:
                score -= 5
        # Soft social prefs (friends / same hall) — RackUp flags
        if prefs.get("prefer_friends") and c.get("is_friend"):
            score += 6
        if prefs.get("prefer_same_hall") and c.get("hall_id") and c.get("hall_id") == player.hall_id:
            score += 4
        scored.append(
            {
                **c,
                "rating_equiv": cr,
                "rating_source": csrc,
                "rating_delta": round(raw_delta, 1),
                "weighted_rating_delta": round(w_delta, 1),
                "rating_weight_applied": weight if disc == "pyramid" else weight,
                "fit_score": round(score, 1),
                "in_window": delta <= window,
                "notes": _notes(player, cr, style, cfg=cfg if disc == "pyramid" else None, disc=disc),
            }
        )
    scored.sort(key=lambda x: x["fit_score"], reverse=True)

    return {
        "player_id": player.player_id,
        "player_rating": pr,
        "player_rating_source": eff.get("source"),
        "band": player.band.value,
        "discipline": disc,
        "pyramid": cfg.to_dict() if disc == "pyramid" else None,
        "cross_league": {
            "enabled": True,
            "player_equivalents": eff.get("equivalents"),
            "note": "Candidates without RackUp rating converted via APA/BCA/TAP/VNEA tables",
        },
        "recommended_window": [-window, window],
        "ranked_candidates": scored[:20],
        "best": scored[0] if scored else None,
        "policy": {
            "avoid_mismatches_over": window * 2,
            "prefer_same_discipline": disc,
            "prefer_same_table_size": cfg.table_size if disc == "pyramid" else None,
            "prefer_same_skill_level": cfg.skill_level if disc == "pyramid" else None,
            "points_to_win": cfg.points_to_win if disc == "pyramid" else None,
            "rating_weight": weight,
            "shared_ladder": True,
        },
    }


def _notes(
    player: PlayerProfile,
    opp_rating: float,
    style: str,
    cfg=None,
    disc: str = "",
) -> str:
    d = opp_rating - float(player.rating or 500)
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
    elif disc:
        base += f" Discipline={disc}."
    return base


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return matchmaking_advice(player, payload)
