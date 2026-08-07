"""Smart matchmaking — ROC Glicko-2 continuous rating + RD (no DB).

Rank on exact rating; widen windows when RD (uncertainty) is high.
Never refuse solely because league systems differ.
Format is a soft preference only. Teams TrueSkill not in this pass.
"""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.games import normalize_discipline
from plugins.rackup_coach.glicko2 import (
    DEFAULT_RD,
    DEFAULT_VOL,
    PlayerRating,
    expected_score,
    matchmaking_uncertainty_window,
    band_for,
)
from plugins.rackup_coach.leagues import (
    format_rating_chip,
    resolve_effective_rating,
)
from plugins.rackup_coach.pyramid import resolve_pyramid, weighted_rating_delta
from plugins.rackup_coach.roc import extract_roc_context, normalize_format
from plugins.rackup_coach.types import PlayerProfile


def _candidate_state(c: dict[str, Any]) -> tuple[PlayerRating, str, float]:
    """Return (PlayerRating, source, confidence)."""
    if c.get("rating") is not None:
        try:
            return (
                PlayerRating(
                    rating=float(c["rating"]),
                    rd=float(c.get("rd") or c.get("rating_deviation") or DEFAULT_RD),
                    volatility=float(
                        c.get("volatility") or c.get("vol") or DEFAULT_VOL
                    ),
                    player_id=str(c.get("player_id") or ""),
                ),
                "rackup",
                0.9,
            )
        except (TypeError, ValueError):
            pass
    if c.get("league_ratings") or c.get("primary_rating_system"):
        eff = resolve_effective_rating(
            {
                "rating": c.get("rating"),
                "rd": c.get("rd"),
                "league_ratings": c.get("league_ratings") or {},
                "league_ratings_meta": c.get("league_ratings_meta") or {},
                "primary_rating_system": c.get("primary_rating_system") or "",
                "matches_played_rackup": int(c.get("matches_played_rackup") or 0),
            }
        )
        return (
            PlayerRating(
                rating=float(eff["rating"]),
                rd=float(eff.get("rd") or DEFAULT_RD),
                volatility=float(eff.get("volatility") or DEFAULT_VOL),
                player_id=str(c.get("player_id") or ""),
            ),
            str(eff.get("source") or "league"),
            float(eff.get("confidence") or 0.6),
        )
    return (
        PlayerRating(rating=500.0, rd=DEFAULT_RD, volatility=DEFAULT_VOL),
        "default_seed",
        0.2,
    )


def matchmaking_advice(
    player: PlayerProfile,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = payload or {}
    roc = extract_roc_context(player, payload)
    candidates = list(payload.get("candidates") or [])
    eff = resolve_effective_rating(player)

    me = PlayerRating(
        rating=float(eff["rating"]),
        rd=float(
            payload.get("rd")
            or getattr(player, "rd", None)
            or eff.get("rd")
            or DEFAULT_RD
        ),
        volatility=float(
            payload.get("volatility")
            or getattr(player, "volatility", None)
            or DEFAULT_VOL
        ),
        player_id=player.player_id,
    )
    pr = me.rating
    disc = normalize_discipline(
        payload.get("discipline")
        or payload.get("game")
        or payload.get("game_style")
        or roc.get("game_style")
        or player.game_style
        or player.discipline
    )
    cfg = resolve_pyramid(player=player, payload=payload)
    weight = float(cfg.rating_weight) if disc == "pyramid" else 1.0

    base_window = float(payload.get("window") or 45.0)
    # Uncertainty-aware window (player RD + optional fixed override)
    window = float(
        payload.get("window")
        or matchmaking_uncertainty_window(me.rd, base_window=base_window)
    )
    if disc == "pyramid":
        window = window / max(weight, 0.5)

    want_format = normalize_format(
        payload.get("format") or roc.get("format") or payload.get("prefer_format")
    )
    prefs = dict(payload.get("preferences") or {})
    scored = []

    for c in candidates:
        opp, csrc, cconf = _candidate_state(c)
        cr = opp.rating
        raw_delta = cr - pr
        w_delta = (
            weighted_rating_delta(raw_delta, cfg.skill_level)
            if disc == "pyramid"
            else raw_delta
        )
        delta = abs(raw_delta)
        # Combined uncertainty widens effective window for this pair
        pair_window = matchmaking_uncertainty_window(
            (me.rd + opp.rd) / 2.0, base_window=window
        )
        style = str(c.get("style") or "balanced")
        exp = expected_score(me, opp)
        score = max(0.0, 100.0 - (delta / max(pair_window, 1)) * 50)
        # Prefer competitive expected scores near 0.5
        score += max(0.0, 10.0 - abs(exp - 0.5) * 40)

        wins = sum(1 for r in (player.recent_results or []) if r.get("won"))
        losses = len(player.recent_results or []) - wins
        if wins > losses and cr > pr:
            score += 8
        if losses > wins and cr < pr:
            score += 8
        if delta <= pair_window:
            score += 15

        c_table = str(c.get("table_size") or "")
        c_skill = str(c.get("skill_level") or c.get("pyramid_skill") or "")
        c_disc = normalize_discipline(
            c.get("discipline") or c.get("game") or c.get("game_style") or disc
        )
        if c_disc == disc:
            score += 8
        if disc == "pyramid":
            if c_table and resolve_pyramid(table_size=c_table).table_size == cfg.table_size:
                score += 12
            if c_skill and c_skill.lower() == cfg.skill_level:
                score += 10
            elif c_skill:
                score -= 5

        c_fmt = normalize_format(c.get("format") or c.get("looking_for_format"))
        if want_format and c_fmt and c_fmt == want_format:
            score += 5
        if prefs.get("prefer_friends") and c.get("is_friend"):
            score += 6
        if (
            prefs.get("prefer_same_hall")
            and c.get("hall_id")
            and c.get("hall_id") == player.hall_id
        ):
            score += 4

        scored.append(
            {
                **c,
                "rating_equiv": cr,
                "rackup_equivalent_used": cr,
                "rd": opp.rd,
                "volatility": opp.volatility,
                "confidence": round(cconf, 2),
                "rating_source": csrc,
                "display": format_rating_chip(cr),
                "band_label": band_for(cr),
                "expected_score_vs_player": round(exp, 4),
                "rating_delta": round(raw_delta, 1),
                "weighted_rating_delta": round(w_delta, 1),
                "pair_window": round(pair_window, 1),
                "fit_score": round(score, 1),
                "in_window": delta <= pair_window,
                "notes": _notes(me, opp, style, cfg=cfg if disc == "pyramid" else None, disc=disc),
            }
        )
    scored.sort(key=lambda x: x["fit_score"], reverse=True)

    return {
        "player_id": player.player_id,
        "player_rating": pr,
        "player_rd": me.rd,
        "player_volatility": me.volatility,
        "player_rating_source": eff.get("source"),
        "player_display": format_rating_chip(pr),
        "band": player.band.value,
        "band_label": band_for(pr),
        "discipline": disc,
        "game_style": disc,
        "ladder": "roc_glicko2",
        "algorithm": "glicko2_v1",
        "pyramid": cfg.to_dict() if disc == "pyramid" else None,
        "roc": {
            "is_roc": bool(roc.get("is_roc") or want_format),
            "roc_league_id": roc.get("roc_league_id"),
            "session_id": roc.get("session_id"),
            "format": want_format or roc.get("format"),
            "format_display": roc.get("format_display"),
        },
        "cross_league": {
            "enabled": True,
            "player_equivalents": eff.get("equivalents"),
            "note": (
                "Candidates without continuous rating converted → ROC seed + high RD. "
                "Rank on exact Glicko rating; RD widens windows."
            ),
            "never_refuse_mixed_systems": True,
        },
        "recommended_window": [-window, window],
        "uncertainty_window_base": round(window, 1),
        "ranked_candidates": scored[:20],
        "best": scored[0] if scored else None,
        "policy": {
            "avoid_mismatches_over": window * 2,
            "prefer_same_discipline": disc,
            "prefer_same_table_size": cfg.table_size if disc == "pyramid" else None,
            "prefer_same_skill_level": cfg.skill_level if disc == "pyramid" else None,
            "prefer_format_soft": want_format,
            "points_to_win": cfg.points_to_win if disc == "pyramid" else None,
            "rating_weight": weight,
            "shared_ladder": True,
            "uses_exact_rating_only": True,
            "uses_rd_uncertainty": True,
            "bands_are_labels_only": True,
            "teams_trueskill": False,
        },
    }


def _notes(
    me: PlayerRating,
    opp: PlayerRating,
    style: str,
    cfg=None,
    disc: str = "",
) -> str:
    d = opp.rating - me.rating
    if abs(d) <= 25:
        base = f"Mirror match ({style}) — ideal skill test."
    elif d > 50:
        base = "Uphill: play patient safeties; don't force early outs."
    elif d < -50:
        base = "Downhill: stay disciplined; no exhibition mistakes."
    else:
        base = f"Competitive window; watch {style} tendencies."
    if me.rd > 120 or opp.rd > 120:
        base += f" High uncertainty (RD me={me.rd:.0f}/opp={opp.rd:.0f})."
    if cfg:
        base += (
            f" Pyramid {cfg.table_size}/{cfg.rack_size}-ball to {cfg.points_to_win} "
            f"(skill weight {cfg.rating_weight}×; ladder=Glicko-2)."
        )
    elif disc:
        base += f" Discipline={disc}."
    return base


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return matchmaking_advice(player, payload)
