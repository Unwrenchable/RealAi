"""RealAI multi-agent runtime — single MessageBus hot path.

Import contract (UNIFY_PLAN step 1)::

    from realai.agent_runtime import MESSAGE_BUS, MultiAgentPipeline, PipelineRunner

Authority module: ``realai/agent_runtime/agent_runtime.py``.
Nested snapshot dirs under this package (including ``_archive_nest/``) are archive-only.
"""

from .agent_runtime import (
    MESSAGE_BUS,
    AgentEdge,
    AgentGraph,
    AgentNode,
    Message,
    MessageBus,
    MultiAgentPipeline,
    PipelineDefinition,
    PipelineRunner,
    PipelineStep,
    run_with_organs,
)

__all__ = [
    "MESSAGE_BUS",
    "AgentEdge",
    "AgentGraph",
    "AgentNode",
    "Message",
    "MessageBus",
    "MultiAgentPipeline",
    "PipelineDefinition",
    "PipelineRunner",
    "PipelineStep",
    "run_with_organs",
]
