"""Agent interfaces and implementations.

Heavy optional agents (planner/worker/critic/…) are lazy so importing
``realai.core.agents.hierarchical_agent`` / ``rise_system`` does not require
legacy ``core.*`` absolute imports to resolve.
"""
from __future__ import annotations

from .base import Agent, AgentContext

__all__ = [
    "Agent",
    "AgentContext",
    "PlannerAgent",
    "WorkerAgent",
    "CriticAgent",
    "SynthesizerAgent",
    "TaskExecutor",
    "AgentSafety",
    "get_agent",
    "get_agent_registry",
    "list_tools",
    "get_llm",
    "HierarchicalAgentSystem",
    "hierarchical_agent",
    "RISESystem",
    "SupervisorAgent",
]


def __getattr__(name: str):
    if name in {"PlannerAgent"}:
        from .planner import PlannerAgent

        return PlannerAgent
    if name in {"WorkerAgent"}:
        from .worker import WorkerAgent

        return WorkerAgent
    if name in {"CriticAgent"}:
        from .critic import CriticAgent

        return CriticAgent
    if name in {"SynthesizerAgent"}:
        from .synthesizer import SynthesizerAgent

        return SynthesizerAgent
    if name in {"TaskExecutor"}:
        from .executor import TaskExecutor

        return TaskExecutor
    if name in {"AgentSafety"}:
        from .safety import AgentSafety

        return AgentSafety
    if name in {"get_agent", "get_agent_registry"}:
        from .agents import get_agent, get_agent_registry

        return get_agent if name == "get_agent" else get_agent_registry
    if name == "list_tools":
        from .tools import list_tools

        return list_tools
    if name == "get_llm":
        from .llm import get_llm

        return get_llm
    if name in {"HierarchicalAgentSystem", "hierarchical_agent"}:
        from .hierarchical_agent import HierarchicalAgentSystem, hierarchical_agent

        return HierarchicalAgentSystem if name == "HierarchicalAgentSystem" else hierarchical_agent
    if name == "RISESystem":
        from .rise_system import RISESystem

        return RISESystem
    if name == "SupervisorAgent":
        from .supervisor import SupervisorAgent

        return SupervisorAgent
    raise AttributeError(name)
