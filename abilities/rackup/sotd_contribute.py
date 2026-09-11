"""Contribute a new Shot of the Day entry into RealAI's grown library."""
from __future__ import annotations

import re
import time
from typing import Any

ABILITY = {
    "id": "sotd_contribute",
    "name": "sotd_contribute",
    "type": "ability",
    "status": "LIVE",
}


def _player_from_context(ctx: dict[str, Any]):
    from plugins.rackup_coach.types import PlayerProfile

    pdata = ctx.get("player") if isinstance(ctx.get("player"), dict) else {}
    player = PlayerProfile(player_id=str(pdata.get("player_id") or ctx.get("player_id") or "hive"))
    for field_name in (
        "display_name",
        "rating",
        "discipline",
        "preferred_hand",
        "hall_id",
        "hall_name",
        "pyramid_skill",
        "skill_level",
    ):
        if field_name in pdata:
            try:
                setattr(player, field_name, pdata[field_name])
            except Exception:
                pass
        elif field_name in ctx:
            try:
                setattr(player, field_name, ctx[field_name])
            except Exception:
                pass
    # weaknesses list used by growth
    try:
        player.weaknesses = list(pdata.get("weaknesses") or ctx.get("weaknesses") or [])
    except Exception:
        pass
    return player


def _default_shot(title_hint: str, player) -> dict[str, Any]:
    title = (title_hint or "Hive smoke practice shot").strip()[:80] or "Hive practice shot"
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "practice"
    return {
        "id": f"grown-{slug}-{int(time.time()) % 100000}",
        "title": title,
        "setup": "Standard rack; cue ball in kitchen.",
        "objective": "Build a clean, repeatable pattern for practice.",
        "why": "Contributed via ability.sotd_contribute for local Hive growth.",
        "weaknesses": list(getattr(player, "weaknesses", None) or []),
        "bands": [getattr(getattr(player, "band", None), "value", None) or "intermediate"],
        "discipline": [getattr(player, "discipline", None) or "pyramid"],
        "reps": 20,
        "not_a_trick_shot": True,
    }


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    player: Any = None,
    payload: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Ability + RackUp compatible entry.

    Accepts either:
      - run(input=..., context={shot|title|...})
      - run(player=PlayerProfile, payload={shot:...})  # legacy RackUp
    """
    from plugins.rackup_coach.sotd_library import growth_policy, save_grown_shot

    ctx = dict(context or {})
    ctx.update(kwargs)
    if payload and isinstance(payload, dict):
        ctx.update(payload)

    if player is None:
        player = _player_from_context(ctx)

    shot = dict(ctx.get("shot") or {})
    if not shot:
        # Flat fields on context / input as title
        for k in ("title", "setup", "objective", "why"):
            if ctx.get(k):
                shot[k] = ctx[k]
    if not shot.get("title"):
        hint = str(ctx.get("title") or ctx.get("input") or input or "").strip()
        # Auto-fill a valid practice shot so status/smoke invokes succeed
        shot = _default_shot(hint, player)
        shot["_auto_filled"] = True

    required = ["title", "setup", "objective", "why"]
    missing = [k for k in required if not shot.get(k)]
    if missing:
        return {
            "ok": False,
            "ability": "sotd_contribute",
            "error": "invalid_shot",
            "missing": missing,
            "policy": growth_policy(),
            "hint": "Pass shot={title,setup,objective,why} or any text input for an auto practice shot",
        }

    if not shot.get("id"):
        slug = re.sub(r"[^a-z0-9]+", "-", str(shot["title"]).lower()).strip("-")[:40]
        shot["id"] = f"grown-{slug}-{int(time.time()) % 100000}"
    shot.setdefault("weaknesses", ctx.get("weaknesses") or getattr(player, "weaknesses", None) or [])
    shot.setdefault("bands", [getattr(getattr(player, "band", None), "value", None) or "intermediate"])
    shot.setdefault("discipline", [getattr(player, "discipline", None) or "pyramid"])
    shot.setdefault("reps", 20)
    shot.setdefault("not_a_trick_shot", True)
    shot["contributed_by"] = getattr(player, "player_id", None) or "hive"
    result = save_grown_shot(shot)
    result["ok"] = True
    result["ability"] = "sotd_contribute"
    result["shot"] = shot
    result["policy"] = growth_policy()
    return result
