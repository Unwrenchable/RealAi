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
        if goal.startswith("shot"):
            ability = payload.get("ability") or "shot_of_the_day"
        if goal.lower().startswith("moderat"):
            ability = payload.get("ability") or "moderation"

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
