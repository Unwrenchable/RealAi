"""Plugin Memory — synthetic organ (first-class hive module)."""
from __future__ import annotations

from typing import Any

from modules.organs.base import Organ, OrganContext, OrganResult


class PluginMemoryOrgan(Organ):
    id = "organ.plugin-memory"
    name = "Plugin Memory"
    category = "memory_ecosystem"
    description = "Plugin state, permissions, marketplace history"
    capabilities = [
        "memory",
        "plugins",
    ]
    hook = "plugins"

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
            if self.hook == "memory":
                from core.memory.bridge import load_long_term_engine, memory_capabilities
                output["memory_capabilities"] = memory_capabilities()
                output["long_term_available"] = load_long_term_engine() is not None
                notes.append("linked core.memory")
            elif self.hook == "training":
                from adapters.training import training_status
                output["training"] = training_status()
                notes.append("linked adapters.training")
            elif self.hook == "orchestration":
                from adapters.agents import list_orchestration_modules
                output["orchestration_modules"] = list_orchestration_modules()
                notes.append("linked orchestration modules")
            elif self.hook == "registry":
                from adapters import load_modules
                output["registry_count"] = len(load_modules())
                notes.append("linked registry")
            elif self.hook in ("planner", "critic", "executor", "synthesizer", "safety"):
                notes.append(f"maps to hierarchical agent role: {self.hook}")
            elif self.hook == "self_improvement":
                notes.append("maps to realai.self_improvement")
            elif self.hook == "identity":
                notes.append("maps to realai.identity")
            else:
                notes.append(f"hook={self.hook} armed")
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
    return PluginMemoryOrgan()
