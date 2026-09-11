"""Shared PlayerProfile builder for RackUp ability wraps (no secrets)."""

from __future__ import annotations

from typing import Any


def player_from_context(context: dict[str, Any] | None = None, **kwargs: Any) -> Any:
    """Build a ``PlayerProfile`` from ability context / kwargs.

    Never reads wallet keys or external secret files — rating fields only.
    """
    from plugins.rackup_coach.types import PlayerProfile

    ctx = dict(context or {})
    ctx.update({k: v for k, v in kwargs.items() if v is not None})
    player_obj = ctx.get("player") if isinstance(ctx.get("player"), dict) else {}
    merged = {**player_obj, **ctx}

    rating = merged.get("rating")
    try:
        rating_f = float(rating) if rating is not None else 500.0
    except (TypeError, ValueError):
        rating_f = 500.0

    kwargs_out: dict[str, Any] = {
        "player_id": str(merged.get("player_id") or merged.get("id") or "anon"),
        "rating": rating_f,
        "discipline": str(
            merged.get("discipline")
            or merged.get("game")
            or merged.get("game_style")
            or "nine_ball"
        ),
    }
    for key in ("rd", "volatility", "table_speed", "weaknesses", "display_name"):
        if key in merged and merged[key] is not None:
            kwargs_out[key] = merged[key]
    return PlayerProfile(**kwargs_out)
