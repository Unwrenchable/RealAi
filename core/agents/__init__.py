"""Agent interfaces and implementations."""

from .base import Agent, AgentContext
from .critic import CriticAgent
from .executor import TaskExecutor
from .planner import PlannerAgent
from .safety import AgentSafety
from .synthesizer import SynthesizerAgent
from .worker import WorkerAgent

# Promoted unique modules (optional imports — tolerate incomplete deps)
try:
    from .hierarchical_agent import *  # noqa: F401,F403
except Exception:
    pass
try:
    from .rise_system import *  # noqa: F401,F403
except Exception:
    pass
try:
    from .supervisor import *  # noqa: F401,F403
except Exception:
    pass
try:
    from .self_heal import *  # noqa: F401,F403
except Exception:
    pass
try:
    from .agent_runtime import *  # noqa: F401,F403
except Exception:
    pass

__all__ = [
    "Agent",
    "AgentContext",
    "PlannerAgent",
    "WorkerAgent",
    "CriticAgent",
    "SynthesizerAgent",
    "TaskExecutor",
    "AgentSafety",
]
