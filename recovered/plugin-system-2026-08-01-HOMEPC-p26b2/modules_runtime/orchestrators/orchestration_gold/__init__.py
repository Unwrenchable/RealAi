"""RealAI Orchestration — multi-agent coordination layer.

This package provides composable primitives for building multi-agent AI
workflows on top of RealAI:

* :class:`~agent.BaseAgent` — a single agent backed by a RealAI client.
* :class:`~orchestrator.Orchestrator` — manages a pool of agents with
  sequential, parallel, and auto-routing execution strategies.
* :class:`~memory.SharedMemory` — thread-safe key/value store shared
  across agents.
* :class:`~tools.ToolRegistry` / :class:`~tools.Tool` — register and
  invoke named capabilities that agents can call.
* :class:`~pipeline.Pipeline` — fixed-sequence agent chain where each
  step's output seeds the next step's task.

Quick-start::

    from realai import RealAIClient
    from realai_orchestration import BaseAgent, Orchestrator, SharedMemory

    client = RealAIClient()
    mem = SharedMemory()

    researcher = BaseAgent(
        name="researcher",
        role="You are an expert research analyst.",
        realai_client=client,
    )
    writer = BaseAgent(
        name="writer",
        role="You are a professional content writer.",
        realai_client=client,
    )

    orch = Orchestrator(client, memory=mem)
    orch.add_agent(researcher)
    orch.add_agent(writer)

    result = orch.run_pipeline("Write a blog post about AI agents.")
    print(result["final_output"])
"""

from .agent import BaseAgent
from .memory import SharedMemory
from .orchestrator import Orchestrator
from .pipeline import Pipeline
from .tools import Tool, ToolRegistry

__all__ = [
    "BaseAgent",
    "Orchestrator",
    "SharedMemory",
    "Pipeline",
    "Tool",
    "ToolRegistry",
]

__version__ = "0.1.0"
