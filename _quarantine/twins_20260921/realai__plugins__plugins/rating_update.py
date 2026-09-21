"""Post-match ROC Glicko-2 rating (RealAI owns the algorithm).

Official ladder: Glicko-2 continuous rating + RD + volatility.
Display bands are labels only. RackUp persists; RealAI never writes DB.

Finalize path: league_validate → (if valid) persist → rating_update.
"""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.games import default_rating_weight, normalize_discipline
from plugins.rackup_coach.glicko2 import (
    DEFAULT_RD,
    DEFAULT_RATING,
    DEFAULT_VOL,
    PlayerRating,
    apply_match_for_player,
    band_for,
    rating_from_player_payload,
    system_info,
)
from plugins.rackup_coach.leagues import (
    format_rating_chip,
    resolve_effective_rating,
)
from plugins.rackup_coach.pyramid import resolve_pyramid
from plugins.rackup_coach.roc import extract_roc_context, format_config, rating_subjects_for_match
from plugins.rackup_coach.types import PlayerProfile, rating_band


def _resolve_outcome(
    player: PlayerProfile,
    payload: dict[str, Any],
    cfg: Any,
) -> tuple[float | None, str | None]:
    """Return (outcome 1/0/0.5, error_hint)."""
    if "won" in payload:
        if payload.get("draw") or payload.get("tie"):
            return 0.5, None
        return (1.0 if payload.get("won") else 0.0), None
    if "my_score" in payload and "opp_score" in payload:
        ms, os_ = int(payload["my_score"]), int(payload["opp_score"])
        target = int(payload.get("points_to_win") or getattr(cfg, "points_to_win", 0) or 0)
        if ms >= target > 0 and os_ < target:
            return 1.0, None
        if os_ >= target > 0 and ms < target:
            return 0.0, None
        if ms == os_:
            return 0.5, None
        return (1.0 if ms > os_ else 0.0), None
    return None, "Provide won:bool or my_score+opp_score"


def _opponent_state(player: PlayerProfile, payload: dict[str, Any]) -> PlayerRating:
    """Build opponent Glicko state from payload / league conversion."""
    opp_id = str(payload.get("opponent_id") or payload.get("opp_id") or "")

    # Explicit continuous rating
    if payload.get("opponent_rating") is not None or payload.get("opp_rating") is not None:
        r = float(payload.get("opponent_rating") or payload.get("opp_rating"))
        rd = float(
            payload.get("opponent_rd")
            or payload.get("opp_rd")
            or payload.get("opponent_rating_deviation")
            or DEFAULT_RD
        )
        vol = float(
            payload.get("opponent_volatility")
            or payload.get("opp_volatility")
            or payload.get("opponent_vol")
            or DEFAULT_VOL
        )
        return PlayerRating(rating=r, rd=rd, volatility=vol, player_id=opp_id)

    # Nested opponent object
    opp_obj = payload.get("opponent") or {}
    if isinstance(opp_obj, dict) and (
        opp_obj.get("rating") is not None or opp_obj.get("league_ratings")
    ):
        if opp_obj.get("rating") is not None:
            return PlayerRating.from_dict(opp_obj, player_id=opp_id or opp_obj.get("player_id", ""))
        eff = resolve_effective_rating(opp_obj)
        return PlayerRating(
            rating=float(eff["rating"]),
            rd=float(eff.get("rd") or DEFAULT_RD),
            volatility=float(eff.get("volatility") or DEFAULT_VOL),
            player_id=str(opp_obj.get("player_id") or opp_id),
        )

    # League-only opponent
    if payload.get("opponent_league_ratings"):
        eff = resolve_effective_rating(
            {
                "rating": None,
                "league_ratings": payload.get("opponent_league_ratings"),
                "league_ratings_meta": payload.get("opponent_league_ratings_meta") or {},
                "primary_rating_system": payload.get("opponent_primary_rating_system") or "",
                "matches_played_rackup": 0,
            }
        )
        return PlayerRating(
            rating=float(eff["rating"]),
            rd=float(eff.get("rd") or DEFAULT_RD),
            volatility=float(eff.get("volatility") or DEFAULT_VOL),
            player_id=opp_id,
        )

    # Fallback: mirror player rating (weak)
    return PlayerRating(
        rating=float(player.rating or DEFAULT_RATING),
        rd=DEFAULT_RD,
        volatility=DEFAULT_VOL,
        player_id=opp_id,
    )


def compute_rating_update(
    player: PlayerProfile,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    RackUp sends match result; RealAI returns Glicko-2 winner_after / loser_after.

    Required:
      won:bool  OR  my_score + opp_score
      opponent_rating (or opponent object / opponent_league_ratings)
    Optional Glicko state:
      rd, volatility (player) — default 175 / 0.06
      opponent_rd, opponent_volatility
    Optional ROC:
      format, session_id, game_style, rating_weight (metadata; Pyramid matrix intact)
    """
    payload = payload or {}
    roc = extract_roc_context(player, payload)
    disc = normalize_discipline(
        payload.get("discipline")
        or payload.get("game")
        or payload.get("game_style")
        or roc.get("game_style")
        or player.game_style
        or player.discipline
    )
    cfg = resolve_pyramid(player=player, payload=payload)
    eff = resolve_effective_rating(player)

    # --- Player Glicko state ---
    # Prefer host continuous rating + RD; else effective convert seed
    if player.rating is not None and (
        int(player.matches_played_rackup or 0) > 0 or not player.league_ratings
    ):
        base_rating = float(player.rating)
        base_rd = float(
            getattr(player, "rd", None)
            or payload.get("rd")
            or payload.get("rating_deviation")
            or DEFAULT_RD
        )
        base_vol = float(
            getattr(player, "volatility", None)
            or payload.get("volatility")
            or payload.get("vol")
            or DEFAULT_VOL
        )
    else:
        base_rating = float(player.rating or eff.get("rating") or DEFAULT_RATING)
        base_rd = float(
            payload.get("rd")
            or getattr(player, "rd", None)
            or eff.get("rd")
            or DEFAULT_RD
        )
        base_vol = float(
            payload.get("volatility")
            or getattr(player, "volatility", None)
            or DEFAULT_VOL
        )

    # Payload overrides for explicit Glicko fields
    if payload.get("rd") is not None:
        base_rd = float(payload["rd"])
    if payload.get("volatility") is not None or payload.get("vol") is not None:
        base_vol = float(payload.get("volatility") or payload.get("vol"))

    me = PlayerRating(
        rating=base_rating,
        rd=base_rd,
        volatility=base_vol,
        player_id=player.player_id,
    )
    opp = _opponent_state(player, payload)

    outcome, err = _resolve_outcome(player, payload, cfg)
    if outcome is None:
        return {"error": "missing_outcome", "hint": err}

    draw = outcome == 0.5
    won = outcome == 1.0

    # Forfeit: still full W/L for ladder (Glicko); flag for audit
    # (product can later dampen; locked path keeps Glicko clean)

    match = apply_match_for_player(me, opp, won=won, draw=draw)
    player_after = match["player_after"]
    opponent_after = match["opponent_after"]
    new_rating = float(player_after["rating"])
    old_rating = me.rating

    # Game weight (Pyramid matrix) — metadata + skill signals; ladder is pure Glicko-2
    if payload.get("rating_weight") is not None:
        weight = float(payload["rating_weight"])
    elif disc == "pyramid" or str(payload.get("game") or "").lower() in (
        "pyramid",
        "rackup-pyramid",
        "rackup_pyramid",
    ):
        weight = float(cfg.rating_weight)
    else:
        weight = float(
            default_rating_weight(
                disc,
                skill_level=payload.get("skill_level") or player.skill_level or "",
            )
        )

    fmt = roc.get("format")
    fcfg = format_config(fmt) if fmt else None
    subjects = rating_subjects_for_match(
        fmt,
        player_ids=list(
            payload.get("player_ids_json")
            or roc.get("player_ids_json")
            or [player.player_id]
        ),
        board_player_ids=list(payload.get("board_player_ids") or []),
    )

    old_display = band_for(old_rating)
    new_display = band_for(new_rating)
    old_coach = rating_band(old_rating).value
    new_coach = rating_band(new_rating).value
    delta = float(match.get("player_delta") or (new_rating - old_rating))

    # Normalize winner/loser for host (always present)
    if draw:
        winner_after = player_after
        loser_after = opponent_after
        winner_before = me.to_dict()
        loser_before = opp.to_dict()
    elif won:
        winner_after = player_after
        loser_after = opponent_after
        winner_before = me.to_dict()
        loser_before = opp.to_dict()
    else:
        winner_after = opponent_after
        loser_after = player_after
        winner_before = opp.to_dict()
        loser_before = me.to_dict()

    return {
        "player_id": player.player_id,
        "algorithm": "glicko2_v1",
        "discipline": disc,
        "game_style": disc,
        "shared_ladder": True,
        "ladder": "roc_glicko2",
        "system": system_info(),
        "pyramid": cfg.to_dict() if disc == "pyramid" else None,
        "roc": {
            "is_roc": bool(roc.get("is_roc") or fmt),
            "roc_league_id": roc.get("roc_league_id"),
            "season_id": roc.get("season_id"),
            "session_id": roc.get("session_id"),
            "match_id": roc.get("match_id") or payload.get("match_id"),
            "format": fmt,
            "format_display": roc.get("format_display"),
            "format_config": fcfg,
            "rating_impact": (fcfg or {}).get("rating_impact"),
            "rating_subjects": subjects,
            "owns_ledger": False,
        },
        "input": {
            "rating_before": me.rating,
            "rd_before": me.rd,
            "volatility_before": me.volatility,
            "opponent_rating": opp.rating,
            "opponent_rd": opp.rd,
            "opponent_volatility": opp.volatility,
            "outcome": outcome,
            "draw": draw,
            "forfeit": bool(payload.get("forfeit")),
            "rating_weight": weight,
            "discipline": disc,
            "effective_rating_source": eff.get("source"),
            "uses_exact_rating_only": True,
            "algorithm": "glicko2_v1",
        },
        # Primary dual update (host writes both when available)
        "winner_before": winner_before,
        "loser_before": loser_before,
        "winner_after": winner_after,
        "loser_after": loser_after,
        "deltas": match.get("deltas") or {
            "winner_rating": round(
                float(winner_after["rating"]) - float(winner_before["rating"]), 3
            ),
            "loser_rating": round(
                float(loser_after["rating"]) - float(loser_before["rating"]), 3
            ),
        },
        # Calling player convenience fields
        "player_before": me.to_dict(),
        "player_after": player_after,
        "opponent_after": opponent_after,
        "rating_before": old_rating,
        "rating_after": new_rating,
        "rd_before": me.rd,
        "rd_after": float(player_after["rd"]),
        "volatility_before": me.volatility,
        "volatility_after": float(player_after["volatility"]),
        "delta": round(delta, 3),
        "raw_delta": round(delta, 3),
        "weighted_delta": round(delta, 3),  # Glicko is primary; weight is metadata
        "display_before": format_rating_chip(old_rating),
        "display_after": format_rating_chip(new_rating),
        "band_label_before": old_display,
        "band_label_after": new_display,
        "band_before": old_coach,
        "band_after": new_coach,
        "band_changed": old_coach != new_coach,
        "display_band_changed": old_display != new_display,
        "skill_signals": {
            "suggested_skill_level": cfg.skill_level if disc == "pyramid" else None,
            "points_to_win_next": cfg.points_to_win if disc == "pyramid" else None,
            "table_size": cfg.table_size if disc == "pyramid" else payload.get("table_size"),
            "rack_size": cfg.rack_size if disc == "pyramid" else None,
            "discipline": disc,
            "pyramid_rating_weight_note": (
                f"Pyramid weight {weight}× is skill-matrix metadata; "
                "competitive ladder is pure Glicko-2."
                if disc == "pyramid"
                else None
            ),
        },
        "league_ratings_note": (
            "APA/BCA/Fargo/TAP/VNEA are not updated here — import/seed only. "
            "After ROC history exists, only Glicko-2 rating_update moves the ladder."
        ),
        "persist_hint": {
            "fields_to_write": [
                "rating",
                "rd",
                "volatility",
                "rating_updated_at",
                "last_match_delta",
            ],
            "write_value": {
                "rating": new_rating,
                "rd": float(player_after["rd"]),
                "volatility": float(player_after["volatility"]),
            },
            "also_write_opponent_if_same_call": {
                "rating": float(opponent_after["rating"]),
                "rd": float(opponent_after["rd"]),
                "volatility": float(opponent_after["volatility"]),
            },
            "owner": "RackUp DB — RealAI does not persist ratings",
            "never_recompute_in_nestjs": True,
        },
    }


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return compute_rating_update(player, payload)
