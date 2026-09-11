"""Orchestration package: live v3 hive + SDK + voice + unified surface.

Live HTTP product: ``realai.orchestration.v3_orchestrator`` (:8001).
Unified inventory/dispatch: ``abilities.orchestration_surface`` /
``realai.orchestration.surface``.
Nests: ``abilities.nest_orchestrators`` (not competing servers).
"""

from .tts_routing import VOICE_ROUTES, hive_voice_entry, route_reply, should_speak

__all__ = [
    "VOICE_ROUTES",
    "hive_voice_entry",
    "route_reply",
    "should_speak",
]

try:
    from .agent import BaseAgent
    from .pipeline import Pipeline
    from .memory import SharedMemory
    from .orchestrator import Orchestrator
    from .tools import Tool, ToolRegistry

    __all__ += [
        "BaseAgent",
        "Pipeline",
        "SharedMemory",
        "Orchestrator",
        "Tool",
        "ToolRegistry",
    ]
except Exception:  # optional gold surface
    pass

try:
    from .surface import ORCH_REGISTRY, run as run_orchestration_surface

    __all__ += ["ORCH_REGISTRY", "run_orchestration_surface"]
except Exception:
    pass
