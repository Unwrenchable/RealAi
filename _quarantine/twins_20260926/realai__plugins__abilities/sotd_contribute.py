"""Contribute a new Shot of the Day entry into RealAI's grown library."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.sotd_library import growth_policy, save_grown_shot
from plugins.rackup_coach.types import PlayerProfile


def run(player: PlayerProfile, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    shot = dict(payload.get("shot") or payload)
    # Minimal validation for growth quality
    required = ["title", "setup", "objective", "why"]
    missing = [k for k in required if not shot.get(k)]
    if missing:
        return {
            "ok": False,
            "error": "invalid_shot",
            "missing": missing,
            "policy": growth_policy(),
        }
    if not shot.get("id"):
        import re
        import time

        slug = re.sub(r"[^a-z0-9]+", "-", str(shot["title"]).lower()).strip("-")[:40]
        shot["id"] = f"grown-{slug}-{int(time.time()) % 100000}"
    shot.setdefault("weaknesses", payload.get("weaknesses") or player.weaknesses or [])
    shot.setdefault("bands", [player.band.value])
    shot.setdefault("discipline", [player.discipline or "pyramid"])
    shot.setdefault("reps", 20)
    shot.setdefault("not_a_trick_shot", True)
    shot["contributed_by"] = player.player_id
    result = save_grown_shot(shot)
    result["shot"] = shot
    result["policy"] = growth_policy()
    return result
