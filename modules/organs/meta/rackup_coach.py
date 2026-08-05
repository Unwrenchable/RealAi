"""RackUp Coach organ — hive-callable entry into the rackup-coach living plugin."""
from __future__ import annotations

from typing import Any

from modules.organs.base import Organ, OrganContext, OrganResult


class RackupCoachOrgan(Organ):
    id = "organ.rackup-coach"
    name = "RackUp Coach"
    category = "meta"
    description = (
        "Professional pool coaching and platform intelligence plugin "
        "(shot of the day, moderation, video, matchmaking, rating, tournaments)."
    )
    capabilities = [
        "coach",
        "shot_of_the_day",
        "moderation",
        "video_analysis",
        "matchmaking",
        "rackup",
        "pool",
        "billiards",
    ]
    hook = "plugins"

    def process(self, ctx: OrganContext) -> OrganResult:
        payload = dict(ctx.payload or {})
        goal = (ctx.goal or "").strip()
        # Allow ability in goal shorthand: "moderation: some text"
        ability = str(payload.get("ability") or payload.get("action") or "coach")
        gl = goal.lower()
        if gl.startswith("shot") or "shot of the day" in gl:
            ability = payload.get("ability") or "shot_of_the_day"
        if gl.startswith("moderat"):
            ability = payload.get("ability") or "moderation"
        if "pyramid" in gl or "points-to" in gl or "10-ball rack" in gl or "15-ball" in gl:
            ability = payload.get("ability") or "pyramid"
        if "pyramid rule" in gl or "rules matrix" in gl:
            ability = "pyramid_rules"

        body: dict[str, Any] = {
            "ability": ability,
            "goal": goal,
            "player": payload.get("player") or payload.get("profile") or {"player_id": "anonymous"},
            "payload": payload.get("payload") or {
                k: v
                for k, v in payload.items()
                if k not in ("ability", "action", "player", "profile", "payload", "goal")
            },
            "organs_enabled": payload.get("organs_enabled", True),
        }
        # If moderation and text at top level
        if ability in ("moderation", "moderate", "chat_moderation") and "text" in payload:
            body["payload"] = {**body.get("payload", {}), "text": payload.get("text")}

        try:
            from plugins.rackup_coach import invoke

            out = invoke(body)
            return OrganResult(
                organ_id=self.id,
                ok=bool(out.get("ok", True)),
                output=out,
                notes=out.get("notes") or f"ability={ability}",
                metrics={"plugin": "rackup-coach", "ability": ability},
            )
        except Exception as e:
            return OrganResult(
                organ_id=self.id,
                ok=False,
                output={"error": str(e)},
                notes=str(e),
            )


def create_organ() -> Organ:
    return RackupCoachOrgan()
