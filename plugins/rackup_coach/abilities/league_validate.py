"""League scorekeeping logic + submission validation (provider-side)."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.pyramid import (
    ball_value,
    resolve_pyramid,
    score_from_balls,
)
from plugins.rackup_coach.types import PlayerProfile


def validate_league_submission(
    player: PlayerProfile,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Validate a league / Pyramid score submission before RackUp persists it.

    Payload:
      game: pyramid | eight_ball | ...
      table_size, skill_level
      my_score, opp_score  (final scores)
      pocketed_balls: [int] optional — for classical recompute
      call_shot_logs: optional [{ball, pocket, made}]
      innings, scratches, opponent_id, match_id
    """
    payload = payload or {}
    cfg = resolve_pyramid(player=player, payload=payload)
    errors: list[str] = []
    warnings: list[str] = []

    my = payload.get("my_score")
    opp = payload.get("opp_score")
    if my is None or opp is None:
        errors.append("my_score and opp_score are required")
        my_i, opp_i = 0, 0
    else:
        try:
            my_i, opp_i = int(my), int(opp)
        except (TypeError, ValueError):
            errors.append("scores must be integers")
            my_i, opp_i = 0, 0

    target = int(payload.get("points_to_win") or cfg.points_to_win)
    is_pyramid = (
        str(payload.get("game") or player.discipline or "").lower() == "pyramid"
        or "pyramid" in str(payload.get("league_format") or "").lower()
    )

    if is_pyramid:
        if my_i < 0 or opp_i < 0:
            errors.append("scores cannot be negative")
        if my_i > target + 20 or opp_i > target + 20:
            warnings.append("score far above target — verify entry")
        # Winner must have reached target (unless forfeit)
        if not payload.get("forfeit"):
            if my_i < target and opp_i < target:
                errors.append(
                    f"neither player reached points_to_win={target}"
                )
            if my_i >= target and opp_i >= target:
                errors.append("both players at/above target — invalid terminal state")
            # Winner should be first to target: winner score >= target, loser < target
            if my_i >= target and opp_i >= target:
                pass
            elif my_i >= target and opp_i >= target:
                errors.append("dual win state")

        # Recompute from pocketed balls if provided
        pocketed = payload.get("pocketed_balls") or payload.get("my_pocketed")
        if pocketed is not None:
            try:
                balls = [int(b) for b in pocketed]
                recomputed = score_from_balls(balls, cfg.rack_size)
                if recomputed != my_i and not payload.get("allow_score_mismatch"):
                    # Soft: warn if mismatch; host may have multi-rack totals
                    if abs(recomputed - my_i) > 0 and payload.get("single_rack"):
                        errors.append(
                            f"pocketed_balls sum to {recomputed} but my_score={my_i}"
                        )
                    else:
                        warnings.append(
                            f"pocketed_balls sum={recomputed} vs my_score={my_i} "
                            "(ok if multi-rack aggregate)"
                        )
                # Validate ball numbers for rack
                max_ball = cfg.rack_size
                for b in balls:
                    if b < 1 or b > max_ball:
                        errors.append(f"invalid ball {b} for {cfg.rack_size}-ball rack")
                    if b == 1 and ball_value(1, cfg.rack_size) != 11:
                        errors.append("1-ball must score 11")
            except (TypeError, ValueError):
                errors.append("pocketed_balls must be list of integers")

        # Call-shot policy
        logs = payload.get("call_shot_logs")
        if cfg.call_shot == "yes" and not logs and not payload.get("forfeit"):
            warnings.append("pro call-shot matches should include call_shot_logs")
        if logs and cfg.call_shot == "no":
            warnings.append("call_shot_logs provided but skill does not require call-shot")

    # Generic league checks
    if payload.get("opponent_id") in (None, "", player.player_id):
        if not payload.get("ghost") and not payload.get("solo_drill"):
            warnings.append("opponent_id missing or self")

    valid = len(errors) == 0
    winner = None
    if valid and is_pyramid and not payload.get("forfeit"):
        if my_i >= target:
            winner = "player"
        elif opp_i >= target:
            winner = "opponent"
    if payload.get("forfeit"):
        winner = "opponent" if payload.get("forfeit_by") == "player" else "player"
        valid = True
        errors = []

    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "pyramid": cfg.to_dict() if is_pyramid else None,
        "normalized": {
            "my_score": my_i,
            "opp_score": opp_i,
            "points_to_win": target,
            "table_size": cfg.table_size,
            "rack_size": cfg.rack_size,
            "skill_level": cfg.skill_level,
            "call_shot": cfg.call_shot,
            "winner": winner,
            "one_ball_value": 11,
        },
        "scorekeeping": {
            "scoring": "classical",
            "ball_n_equals_n": True,
            "ball_1": 11,
            "cue_ball": "designated_only",
            "win_condition": "first_to_target",
        },
        "persist_hint": {
            "accept": valid,
            "owner": "RackUp DB writes only if valid==true",
            "next_call": "rating_update after accept",
        },
    }


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return validate_league_submission(player, payload)
