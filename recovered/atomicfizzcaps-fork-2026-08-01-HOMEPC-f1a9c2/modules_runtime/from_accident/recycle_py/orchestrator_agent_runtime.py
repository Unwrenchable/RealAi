"""
RealAI Multi-Agent Runtime
===========================
Provides MessageBus, PipelineRunner, and AgentGraph for multi-agent orchestration.

Usage::

    from realai.agent_runtime import MESSAGE_BUS, PipelineRunner

    MESSAGE_BUS.subscribe("agent1", lambda msg: print(msg.content))
    MESSAGE_BUS.send("orchestrator", "agent1", "Hello")
"""

from __future__ import annotations

import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Message:
    """A message exchanged between agents.

    Attributes:
        id: Unique message identifier.
        from_agent: Sender agent ID.
        to_agent: Recipient agent ID.
        content: Message content (any serializable type).
        timestamp: Unix timestamp of creation.
        metadata: Optional extra metadata dict.
    """
    id: str
    from_agent: str
    to_agent: str
    content: Any
    timestamp: float
    metadata: Dict = field(default_factory=dict)


class MessageBus:
    """Thread-unsafe in-memory message bus for agent communication.

    Agents subscribe with handlers that are called synchronously on send().
    """

    def __init__(self) -> None:
        """Initialize an empty message bus."""
        self._handlers: Dict[str, Callable[[Message], None]] = {}
        self._inboxes: Dict[str, deque] = {}

    def send(
        self,
        from_agent: str,
        to_agent: str,
        content: Any,
        metadata: Optional[Dict] = None,
    ) -> str:
        """Send a message from one agent to another.

        Args:
            from_agent: Sender agent ID.
            to_agent: Recipient agent ID.
            content: Message payload.
            metadata: Optional metadata dict.

        Returns:
            The generated message ID string.
        """
        msg = Message(
            id=str(uuid.uuid4()),
            from_agent=from_agent,
            to_agent=to_agent,
            content=content,
            timestamp=time.time(),
            metadata=metadata or {},
        )
        if to_agent not in self._inboxes:
            self._inboxes[to_agent] = deque()
        self._inboxes[to_agent].append(msg)
        handler = self._handlers.get(to_agent)
        if handler:
            try:
                handler(msg)
            except Exception:
                pass
        return msg.id

    def subscribe(self, agent_id: str, handler: Callable[[Message], None]) -> None:
        """Subscribe an agent to receive messages.

        Args:
            agent_id: The agent's unique ID.
            handler: Callable invoked with each incoming Message.
        """
        self._handlers[agent_id] = handler
        if agent_id not in self._inboxes:
            self._inboxes[agent_id] = deque()

    def unsubscribe(self, agent_id: str) -> None:
        """Unsubscribe an agent.

        Args:
            agent_id: The agent ID to remove.
        """
        self._handlers.pop(agent_id, None)

    def get_messages(self, agent_id: str, limit: int = 50) -> List[Message]:
        """Return the inbox for an agent.

        Args:
            agent_id: Agent whose inbox to retrieve.
            limit: Maximum number of messages to return.

        Returns:
            List of Message objects (oldest first), up to limit.
        """
        inbox = self._inboxes.get(agent_id, deque())
        msgs = list(inbox)
        return msgs[-limit:] if len(msgs) > limit else msgs

    def broadcast(self, from_agent: str, content: Any) -> List[str]:
        """Send content to all subscribed agents.

        Args:
            from_agent: Sender agent ID.
            content: Message payload.

        Returns:
            List of generated message IDs.
        """
        ids = []
        for agent_id in list(self._handlers.keys()):
            if agent_id != from_agent:
                msg_id = self.send(from_agent, agent_id, content)
                ids.append(msg_id)
        return ids


@dataclass
class PipelineStep:
    """A single step in an agent pipeline.

    Attributes:
        agent_id: The agent to execute this step.
        task_template: Task description template (may contain {input}).
        input_key: Key name for input data.
        output_key: Key name for output data.
    """
    agent_id: str
    task_template: str
    input_key: str = "input"
    output_key: str = "output"


@dataclass
class PipelineDefinition:
    """Definition of a multi-step agent pipeline.

    Attributes:
        id: Unique pipeline identifier.
        name: Human-readable pipeline name.
        steps: Ordered list of pipeline steps.
        description: Optional pipeline description.
    """
    id: str
    name: str
    steps: List[PipelineStep]
    description: str = ""


class PipelineRunner:
    """Executes agent pipelines step by step.

    Each step's output becomes the next step's input.
    """

    def run(
        self,
        pipeline: PipelineDefinition,
        initial_input: str,
        agent_registry: Any,
    ) -> Dict[str, Any]:
        """Execute a pipeline with the given input.

        Args:
            pipeline: PipelineDefinition to execute.
            initial_input: Starting input string.
            agent_registry: AgentRegistry instance for executing agents.

        Returns:
            Dict with pipeline_id, steps_completed, result, and step_results.
        """
        current_input = initial_input
        step_results = []
        steps_completed = 0

        for step in pipeline.steps:
            task = step.task_template.replace("{input}", str(current_input))
            task = task.replace("{" + step.input_key + "}", str(current_input))

            try:
                if hasattr(agent_registry, "execute_agent"):
                    result = agent_registry.execute_agent(
                        agent_id=step.agent_id,
                        task=task,
                    )
                else:
                    result = {"status": "success", "result": task}

                output = result.get("result", result.get("output", str(result)))
                step_results.append({
                    "step": steps_completed + 1,
                    "agent_id": step.agent_id,
                    "input": current_input,
                    "output": output,
                })
                current_input = output
                steps_completed += 1
            except Exception as e:
                step_results.append({
                    "step": steps_completed + 1,
                    "agent_id": step.agent_id,
                    "error": str(e),
                })
                break

        return {
            "pipeline_id": pipeline.id,
            "steps_completed": steps_completed,
            "result": current_input,
            "step_results": step_results,
        }


@dataclass
class AgentNode:
    """A node in an agent execution graph.

    Attributes:
        agent_id: The agent's unique identifier.
        task_template: Task template for this node.
    """
    agent_id: str
    task_template: str


@dataclass
class AgentEdge:
    """An edge in an agent execution graph.

    Attributes:
        from_node: Source agent ID.
        to_node: Destination agent ID.
        condition: Optional condition string for conditional traversal.
    """
    from_node: str
    to_node: str
    condition: Optional[str] = None


class AgentGraph:
    """Directed graph of agents for parallel/conditional execution.

    Supports BFS execution from entrypoint nodes.
    """

    def __init__(self) -> None:
        """Initialize an empty agent graph."""
        self._nodes: Dict[str, AgentNode] = {}
        self._edges: List[AgentEdge] = []

    def add_node(self, node: AgentNode) -> None:
        """Add a node to the graph.

        Args:
            node: AgentNode to add.
        """
        self._nodes[node.agent_id] = node

    def add_edge(self, edge: AgentEdge) -> None:
        """Add an edge to the graph.

        Args:
            edge: AgentEdge to add.
        """
        self._edges.append(edge)

    def get_entrypoints(self) -> List[str]:
        """Return node IDs with no incoming edges.

        Returns:
            List of agent IDs that are graph entrypoints.
        """
        has_incoming = {e.to_node for e in self._edges}
        return [nid for nid in self._nodes if nid not in has_incoming]

    def execute(
        self,
        initial_input: str,
        agent_registry: Any,
    ) -> Dict[str, Any]:
        """Execute the graph via BFS from entrypoints.

        Args:
            initial_input: Starting input for entrypoint nodes.
            agent_registry: AgentRegistry for executing agents.

        Returns:
            Dict with all_results (per-agent), steps_run, and final_outputs.
        """
        results: Dict[str, Any] = {}
        queue = []
        visited = set()

        for entry in self.get_entrypoints():
            queue.append((entry, initial_input))

        if not queue and self._nodes:
            # No entrypoints — start from first node
            first = next(iter(self._nodes))
            queue.append((first, initial_input))

        while queue:
            agent_id, agent_input = queue.pop(0)
            if agent_id in visited:
                continue
            visited.add(agent_id)

            node = self._nodes.get(agent_id)
            if not node:
                continue

            task = node.task_template.replace("{input}", str(agent_input))
            try:
                if hasattr(agent_registry, "execute_agent"):
                    result = agent_registry.execute_agent(
                        agent_id=agent_id,
                        task=task,
                    )
                else:
                    result = {"status": "success", "result": task}
                output = result.get("result", str(result))
            except Exception as e:
                output = "Error: {0}".format(e)
                result = {"status": "error", "result": output}

            results[agent_id] = result

            # Enqueue successors
            for edge in self._edges:
                if edge.from_node == agent_id and edge.to_node not in visited:
                    queue.append((edge.to_node, output))

        return {
            "all_results": results,
            "steps_run": len(results),
            "final_outputs": {
                aid: r.get("result", "") for aid, r in results.items()
            },
        }


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

MESSAGE_BUS = MessageBus()
