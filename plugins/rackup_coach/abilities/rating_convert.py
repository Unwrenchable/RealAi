"""Cross-league rating conversion (APA/BCA/TAP/VNEA ↔ RackUp)."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.leagues import convert_rating, resolve_effective_rating
from plugins.rackup_coach.types import PlayerProfile


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = dict(payload or {})
    # If no from_system, use player's primary league ratings
    if payload.get("from_value") is None and payload.get("value") is None:
        lr = player.league_ratings or {}
        meta = player.league_ratings_meta or {}
        primary = (player.primary_rating_system or "").lower()
        if primary and lr.get(primary) is not None:
            payload["from_system"] = primary
            payload["from_value"] = lr.get(primary)
            payload["from_scale"] = (meta.get(primary) or {}).get("scale") or "auto"
        else:
            for sys in ("apa", "bca", "tap", "vnea"):
                if lr.get(sys) is not None:
                    payload["from_system"] = sys
                    payload["from_value"] = lr.get(sys)
                    payload["from_scale"] = (meta.get(sys) or {}).get("scale") or "auto"
                    break
        # pass also_known from remaining
        also = []
        for sys, val in (lr.items() if isinstance(lr, dict) else []):
            if val is None:
                continue
            if sys == payload.get("from_system"):
                continue
            also.append({
                "system": sys,
                "value": val,
                "scale": (meta.get(sys) or {}).get("scale") or "auto",
                **({k: v for k, v in (meta.get(sys) or {}).items() if k != "scale"}),
            })
        if also:
            payload["also_known"] = also

    result = convert_rating(payload)
    result["player_id"] = player.player_id
    result["effective_for_player"] = resolve_effective_rating(player)
    result["shared_rating_current"] = player.rating
    return result
