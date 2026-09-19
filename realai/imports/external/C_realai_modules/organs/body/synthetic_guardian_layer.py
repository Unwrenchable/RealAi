"""Synthetic Guardian Layer — policy envelope for tool effectors."""
from __future__ import annotations

from typing import Any

from modules.organs.base import Organ, OrganContext, OrganResult


class SyntheticGuardianLayerOrgan(Organ):
    id = "organ.synthetic-guardian-layer"
    name = "Synthetic Guardian Layer"
    category = "body"
    description = (
        "Policy envelope and permission sandbox for effectors. "
        "Default REALAI_GUARDIAN_MODE=advisory; set hard_block to enforce."
    )
    capabilities = [
        "guardian",
        "policy",
        "permissions",
        "tool_safety",
    ]
    hook = "safety"

    def process(self, ctx: OrganContext) -> OrganResult:
        goal = (ctx.goal or "").strip()
        payload = dict(ctx.payload or {})
        output: dict[str, Any] = {
            "organ": self.id,
            "name": self.name,
            "hook": self.hook,
            "goal": goal,
            "category": self.category,
            "payload_keys": sorted(payload.keys()),
        }
        notes: list[str] = []
        try:
            from realai.guardian import check_tool_call, guardian_mode

            mode = guardian_mode()
            output["guardian_mode"] = mode
            tool_name = str(payload.get("tool_name") or payload.get("tool") or "")
            arguments = payload.get("arguments") or payload.get("args") or {}
            if tool_name:
                try:
                    from realai.tools import TOOL_REGISTRY

                    schema = TOOL_REGISTRY.get(tool_name)
                except Exception:
                    schema = None
                if schema is None:
                    # Synthetic schema for advisory check
                    class _S:
                        safety_level = str(payload.get("safety_level") or "safe")
                        source = str(payload.get("source") or "unknown")
                        ability_status = str(payload.get("ability_status") or "")

                    schema = _S()
                decision = check_tool_call(tool_name, arguments if isinstance(arguments, dict) else {}, schema)
                output["decision"] = decision
                notes.append(f"mode={mode} decision={decision.get('decision')}")
            else:
                output["decision"] = {
                    "mode": mode,
                    "policy": (
                        "advisory default — set REALAI_GUARDIAN_MODE=hard_block to enforce tool blocks"
                    ),
                }
                notes.append(f"guardian armed mode={mode}")
            notes.append("maps to realai.guardian + ToolCallValidator")
        except Exception as e:
            notes.append(f"soft-fail: {e}")
        return OrganResult(
            organ_id=self.id,
            ok=True,
            output=output,
            notes="; ".join(notes),
            metrics={"capabilities": len(self.capabilities)},
        )


def create_organ() -> Organ:
    return SyntheticGuardianLayerOrgan()
