"""Synthetic organ base types for RealAI hive."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class OrganContext:
    """Runtime context passed into organ.process()."""
    goal: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    memory: Any = None
    tools: Any = None
    agent_runtime: Any = None


@dataclass
class OrganResult:
    organ_id: str
    ok: bool
    output: Any = None
    notes: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)


class Organ:
    """First-class callable synthetic organ (not chat-only concept)."""

    id: str = "organ.base"
    name: str = "Base Organ"
    category: str = "meta"
    description: str = ""
    capabilities: list[str] = []

    def process(self, ctx: OrganContext) -> OrganResult:
        raise NotImplementedError

    def info(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "capabilities": list(self.capabilities),
            "callable": True,
        }
