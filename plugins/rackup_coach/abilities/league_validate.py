"""League scorekeeping logic + submission validation (provider-side)."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.games import game_knowledge, normalize_discipline
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
    Validate a league / Pyramid / race score submission before RackUp persists it.

    Payload:
      game: pyramid | eight_ball | nine_ball | ten_ball | one_pocket
      table_size, skill_level
      my_score, opp_score  (final scores or games won)
      race_to, pocketed_balls, call_shot_logs, forfeit, opponent_id, match_id
    """
    payload = payload or {}
    disc = normalize_discipline(
        payload.get("game") or payload.get("discipline") or player.discipline
    )
    gk = game_knowledge(disc)
    cfg = resolve_pyramid(player=player, payload=payload)
    errors: list[str] = []
    warnings: list[str] = []

    my = payload.get("my_score")
    opp = payload.get("opp_score")
    # Boolean win-only matches (some 8-ball single games)
    if my is None and opp is None and "won" in payload:
        my_i = 1 if payload.get("won") else 0
        opp_i = 0 if payload.get("won") else 1
    elif my is None or opp is None:
        errors.append("my_score and opp_score are required (or won:bool)")
        my_i, opp_i = 0, 0
    else:
        try:
            my_i, opp_i = int(my), int(opp)
        except (TypeError, ValueError):
            errors.append("scores must be integers")
            my_i, opp_i = 0, 0

    is_pyramid = disc == "pyramid"
    race_to = int(
        payload.get("race_to")
        or player.race_to
        or (gk.get("validation") or {}).get("typical_race")
        or 0
    )
    target = int(
        payload.get("points_to_win")
        or (cfg.points_to_win if is_pyramid else race_to or 0)
    )

    if my_i < 0 or opp_i < 0:
        errors.append("scores cannot be negative")

    if is_pyramid:
        if my_i > target + 20 or opp_i > target + 20:
            warnings.append("score far above target — verify entry")
        if not payload.get("forfeit"):
            if target > 0 and my_i < target and opp_i < target:
                errors.append(f"neither player reached points_to_win={target}")
            if target > 0 and my_i >= target and opp_i >= target:
                errors.append("both players at/above target — invalid terminal state")

        pocketed = payload.get("pocketed_balls") or payload.get("my_pocketed")
        if pocketed is not None:
            try:
                balls = [int(b) for b in pocketed]
                recomputed = score_from_balls(balls, cfg.rack_size)
                if recomputed != my_i and not payload.get("allow_score_mismatch"):
                    if abs(recomputed - my_i) > 0 and payload.get("single_rack"):
                        errors.append(
                            f"pocketed_balls sum to {recomputed} but my_score={my_i}"
                        )
                    else:
                        warnings.append(
                            f"pocketed_balls sum={recomputed} vs my_score={my_i} "
                            "(ok if multi-rack aggregate)"
                        )
                max_ball = cfg.rack_size
                for b in balls:
                    if b < 1 or b > max_ball:
                        errors.append(f"invalid ball {b} for {cfg.rack_size}-ball rack")
            except (TypeError, ValueError):
                errors.append("pocketed_balls must be list of integers")

        logs = payload.get("call_shot_logs")
        if cfg.call_shot == "yes" and not logs and not payload.get("forfeit"):
            warnings.append("pro call-shot matches should include call_shot_logs")
        if logs and cfg.call_shot == "no":
            warnings.append("call_shot_logs provided but skill does not require call-shot")
    else:
        # Race games (9/10-ball, one-pocket) and 8-ball games won
        if target > 0 and not payload.get("forfeit"):
            if my_i < target and opp_i < target:
                # single game may use 0/1
                if not (my_i + opp_i == 1 and max(my_i, opp_i) == 1):
                    errors.append(
                        f"neither player reached race_to/points target={target}"
                    )
            if my_i >= target and opp_i >= target:
                errors.append("both players at/above race target")
        if disc == "one_pocket" and target <= 0:
            warnings.append("one_pocket typically race_to=8 — set race_to")
        if disc == "ten_ball":
            warnings.append("ensure call-shot discipline logged when ruleset=WPA")

    if payload.get("opponent_id") in (None, "", player.player_id):
        if not payload.get("ghost") and not payload.get("solo_drill"):
            warnings.append("opponent_id missing or self")

    valid = len(errors) == 0
    winner = None
    if valid and not payload.get("forfeit"):
        if target > 0:
            if my_i >= target and opp_i < target:
                winner = "player"
            elif opp_i >= target and my_i < target:
                winner = "opponent"
        elif my_i > opp_i:
            winner = "player"
        elif opp_i > my_i:
            winner = "opponent"
    if payload.get("forfeit"):
        winner = "opponent" if payload.get("forfeit_by") == "player" else "player"
        valid = True
        errors = []

    scorekeeping = (
        {
            "scoring": "classical",
            "ball_n_equals_n": True,
            "ball_1": 11,
            "cue_ball": "designated_only",
            "win_condition": "first_to_target",
        }
        if is_pyramid
        else {
            "scoring": (gk.get("validation") or {}).get("score_type") or "race",
            "discipline": disc,
            "display": gk.get("display"),
            "win_condition": "race_or_game",
            "typical_race": (gk.get("validation") or {}).get("typical_race"),
        }
    )

    return {
        "valid": valid,
        "errors": errors,
        "warnings": warnings,
        "discipline": disc,
        "game_knowledge": {
            "display": gk.get("display"),
            "objective": gk.get("objective"),
        },
        "pyramid": cfg.to_dict() if is_pyramid else None,
        "normalized": {
            "my_score": my_i,
            "opp_score": opp_i,
            "points_to_win": target if is_pyramid else None,
            "race_to": target if not is_pyramid and target else race_to or None,
            "table_size": cfg.table_size if is_pyramid else payload.get("table_size"),
            "rack_size": cfg.rack_size if is_pyramid else None,
            "skill_level": cfg.skill_level if is_pyramid else player.skill_level,
            "call_shot": cfg.call_shot if is_pyramid else None,
            "winner": winner,
            "one_ball_value": 11 if is_pyramid else None,
            "discipline": disc,
        },
        "scorekeeping": scorekeeping,
        "persist_hint": {
            "accept": valid,
            "owner": "RackUp DB writes only if valid==true",
            "next_call": "rating_update after accept",
        },
    }


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return validate_league_submission(player, payload)
