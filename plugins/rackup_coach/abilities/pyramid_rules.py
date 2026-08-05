"""Pyramid rules exposure + mid-game race advice."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.pyramid import (
    ball_value,
    classical_mindset_tips,
    pyramid_matrix,
    race_context,
    resolve_pyramid,
    score_from_balls,
)
from plugins.rackup_coach.types import PlayerProfile


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    cfg = resolve_pyramid(player=player, payload=payload)
    my = int(payload.get("my_score", player.pyramid_score) or 0)
    opp = int(payload.get("opp_score", player.pyramid_opp_score) or 0)
    pocketed = payload.get("pocketed_balls") or payload.get("balls") or []
    scored = None
    if pocketed:
        scored = score_from_balls([int(b) for b in pocketed], cfg.rack_size)

    return {
        "game": "RackUp Pyramid",
        "config": cfg.to_dict(),
        "matrix": pyramid_matrix(),
        "race": race_context(cfg, my_score=my, opp_score=opp),
        "classical_mindset": classical_mindset_tips(cfg),
        "innings_score_from_balls": scored,
        "one_ball_value": ball_value(1, cfg.rack_size),
        "coaching_summary": (
            f"{cfg.table_size} → {cfg.rack_size}-ball rack | "
            f"{cfg.skill_level} first to {cfg.points_to_win} | "
            f"call_shot={cfg.call_shot} | rating_weight={cfg.rating_weight}×"
        ),
    }
