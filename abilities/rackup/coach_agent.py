"""Core RackUp Coach agent — routes abilities + organs."""
from __future__ import annotations

from typing import Any

from plugins.rackup_coach.abilities import run_ability
from plugins.rackup_coach.organs_bridge import run_organs_for_ability
from plugins.rackup_coach.types import CoachRequest, CoachResponse, PlayerProfile


class RackUpCoachAgent:
    """Professional pool coach agent (provider-level) — ROC-aware."""

    name = "rackup-coach"
    version = "1.6.0"

    def handle(self, request: CoachRequest | dict[str, Any]) -> CoachResponse:
        if isinstance(request, dict):
            request = CoachRequest.from_dict(request)

        ability = (request.ability or "coach").strip().lower()
        player = request.player
        payload = dict(request.payload or {})
        if request.goal and "goal" not in payload:
            payload["goal"] = request.goal
        # Map game_style → discipline for ROC hosts
        if payload.get("game_style") and not payload.get("discipline") and not payload.get("game"):
            payload["game"] = payload["game_style"]
        if player.game_style and (not player.discipline or player.discipline == "eight_ball"):
            # leave player as-is; abilities read game_style
            pass
        # Auto-tag Pyramid when discipline/table implies it
        disc_hint = (
            (player.discipline or "")
            or (player.game_style or "")
            or str(payload.get("game") or payload.get("game_style") or "")
        ).lower()
        if disc_hint == "pyramid" or "pyramid" in disc_hint:
            payload.setdefault("game", "pyramid")
            if ability in ("coach", "professional_coach", "session"):
                ability = "pyramid" if ability != "pyramid_rules" else ability

        # 1) Organs first — cognitive/memory stack for this ability
        goal = request.goal or f"{ability} for {player.display_name or player.player_id}"
        try:
            pyr = player.pyramid_config(payload).to_dict()
        except Exception:
            pyr = {}
        try:
            from plugins.rackup_coach.roc import extract_roc_context

            roc_ctx = extract_roc_context(player, payload)
        except Exception:
            roc_ctx = {}
        organ_payload = {
            "player": player.to_dict(),
            "ability": ability,
            "plugin": "rackup-coach",
            "pyramid": pyr,
            "roc": roc_ctx,
        }
        organ_trace = run_organs_for_ability(
            ability,
            goal=goal,
            payload=organ_payload,
            enabled=request.organs_enabled,
        )

        # 2) Ability implementation
        try:
            result = run_ability(ability, player, payload)
            if isinstance(result, dict) and result.get("error"):
                return CoachResponse(
                    ok=False,
                    ability=ability,
                    result=result,
                    organ_trace=organ_trace,
                    error=str(result.get("error")),
                )
            chip = getattr(player, "rating_chip", None) or f"rating={player.rating}"
            fmt = (roc_ctx or {}).get("format") or ""
            notes = f"chip={chip} band={player.band.value}"
            if fmt:
                notes += f" format={fmt}"
            return CoachResponse(
                ok=True,
                ability=ability,
                result=result if isinstance(result, dict) else {"value": result},
                organ_trace=organ_trace,
                notes=notes,
            )
        except Exception as e:
            return CoachResponse(
                ok=False,
                ability=ability,
                result={},
                organ_trace=organ_trace,
                error=str(e),
            )

    def shot_of_the_day(self, player: dict | PlayerProfile, **kwargs: Any) -> dict[str, Any]:
        req = CoachRequest(
            ability="shot_of_the_day",
            player=player if isinstance(player, PlayerProfile) else PlayerProfile.from_dict(player),
            payload=kwargs,
        )
        return self.handle(req).to_dict()

    def moderate(self, text: str, player: dict | PlayerProfile | None = None, **kwargs: Any) -> dict[str, Any]:
        p = player if isinstance(player, PlayerProfile) else PlayerProfile.from_dict(player or {"player_id": "anon"})
        req = CoachRequest(
            ability="moderation",
            player=p,
            payload={"text": text, **kwargs},
        )
        return self.handle(req).to_dict()

    def coach(self, player: dict | PlayerProfile, mode: str = "full", goal: str = "", **kwargs: Any) -> dict[str, Any]:
        p = player if isinstance(player, PlayerProfile) else PlayerProfile.from_dict(player)
        req = CoachRequest(
            ability="coach",
            player=p,
            goal=goal,
            payload={"mode": mode, **kwargs},
        )
        return self.handle(req).to_dict()


# Singleton used by plugin entrypoints
COACH = RackUpCoachAgent()
