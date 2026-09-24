"""RealAI hierarchical multi-agent system.

Gold bodies: ``realai.core.agents`` (rise_system, supervisor, hierarchical_agent, …).
Agency specialists: ``agents.hierarchical.agency`` (persona MD under ``agents/agency/``).

Imports are soft: missing optional deps (langchain/langgraph) do not break package import.
"""
from __future__ import annotations

HierarchicalAgentSystem = None  # type: ignore
hierarchical_agent = None  # type: ignore
RISESystem = None  # type: ignore
SupervisorAgent = None  # type: ignore
AgentState = None  # type: ignore
_IMPORT_ERROR: str | None = None

try:
    from realai.core.agents.rise_system import RISESystem
    from realai.core.agents.supervisor import SupervisorAgent, AgentState
except Exception as exc:  # pragma: no cover
    _IMPORT_ERROR = f"rise/supervisor: {exc}"

try:
    from realai.core.agents.hierarchical_agent import HierarchicalAgentSystem, hierarchical_agent
except Exception as exc:  # pragma: no cover
    _IMPORT_ERROR = ((_IMPORT_ERROR + "; ") if _IMPORT_ERROR else "") + f"hierarchical: {exc}"

from .agency import (  # noqa: E402
    DIVISION_TO_SPECIALIST,
    get_agency_specialist,
    list_agency_agents,
    list_agency_divisions,
    load_agency_persona,
    map_division_to_specialist,
)

__all__ = [
    "HierarchicalAgentSystem",
    "hierarchical_agent",
    "RISESystem",
    "SupervisorAgent",
    "AgentState",
    "_IMPORT_ERROR",
    "list_agency_agents",
    "list_agency_divisions",
    "get_agency_specialist",
    "load_agency_persona",
    "map_division_to_specialist",
    "DIVISION_TO_SPECIALIST",
]
