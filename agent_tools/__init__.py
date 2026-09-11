"""Living agent_tools package (promoted from agent_tools_gold).

Canonical import::

    from agent_tools.registry import load_agents, load_profiles
    from agent_tools.tooling.registry import ToolRegistry
"""

from __future__ import annotations

__all__ = [
    "__version__",
    "load_agents",
    "load_profiles",
    "assess_agent_access",
    "ToolRegistry",
    "package_status",
]
__version__ = "0.2.0"


def __getattr__(name: str):
    if name in ("load_agents", "load_profiles", "assess_agent_access", "package_status"):
        from . import registry as _reg

        return getattr(_reg, name)
    if name == "ToolRegistry":
        from .tooling.registry import ToolRegistry

        return ToolRegistry
    raise AttributeError(name)
