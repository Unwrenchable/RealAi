"""Multi-agent orchestration engine for RealAI.

The Orchestrator manages a named pool of :class:`~agent.BaseAgent` instances
and provides three execution strategies:

* **Sequential pipeline** – agents run one after another, each receiving the
  accumulated context from all previous agents.
* **Parallel execution** – independent tasks are distributed across agents
  concurrently using threads.
* **Auto-routing** – the orchestrator selects the best-matched agent for a
  task based on keyword matching against agent role descriptions.
"""

import threading
from typing import Any, Dict, List, Optional

from .agent import BaseAgent
from .memory import SharedMemory


class Orchestrator:
    """Manages a pool of agents and coordinates multi-agent workflows.

    Args:
        realai_client: Shared RealAI client passed to agents that don't
            supply their own (currently informational — agents carry their
            own client references).
        memory: Optional :class:`~memory.SharedMemory` instance.  A new one
            is created automatically if not provided.

    Example::

        from realai import RealAIClient
        from realai_orchestration.agent import BaseAgent
        from realai_orchestration.orchestrator import Orchestrator

        client = RealAIClient()
        orch = Orchestrator(client)
        orch.add_agent(BaseAgent("researcher", "Research AI topics.", client))
        orch.add_agent(BaseAgent("writer", "Write a blog post.", client))
        result = orch.run_pipeline("Write about large language models.")
    """

    def __init__(
        self,
        realai_client: Any,
        memory: Optional[SharedMemory] = None,
    ) -> None:
        self.realai_client = realai_client
        self.memory: SharedMemory = memory or SharedMemory()
        self._agents: Dict[str, BaseAgent] = {}

    # ------------------------------------------------------------------
    # Agent management
    # ------------------------------------------------------------------

    def add_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the orchestrator.

        Args:
            agent: :class:`~agent.BaseAgent` to register.

        Raises:
            ValueError: If an agent with the same name is already registered.
        """
        if agent.name in self._agents:
            raise ValueError(
                f"An agent named '{agent.name}' is already registered."
            )
        self._agents[agent.name] = agent

    def remove_agent(self, name: str) -> bool:
        """Unregister an agent by name.

        Args:
            name: Agent name to remove.

        Returns:
            True if found and removed, False otherwise.
        """
        if name in self._agents:
            del self._agents[name]
            return True
        return False

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """Retrieve an agent by name.

        Args:
            name: Agent name.

        Returns:
            The :class:`~agent.BaseAgent`, or None if not registered.
        """
        return self._agents.get(name)

    @property
    def agents(self) -> Dict[str, BaseAgent]:
        """Read-only view of the registered agents."""
        return dict(self._agents)

    # ------------------------------------------------------------------
    # Execution strategies
    # ------------------------------------------------------------------

    def run_pipeline(
        self,
        task: str,
        agents: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Run agents sequentially, each passing its output as context.

        Args:
            task: Initial task description given to the first agent.
            agents: Ordered list of agent names to run.  If omitted, all
                registered agents are run in insertion order.

        Returns:
            Dict with:
                - ``final_output``: The last agent's output text.
                - ``steps``: List of per-agent result dicts.
                - ``memory``: Final shared memory snapshot.
                - ``success``: True if every step succeeded.
        """
        agent_names = agents or list(self._agents.keys())
        steps: List[Dict[str, Any]] = []
        context: Dict[str, Any] = self.memory.get_context()
        current_task = task

        for name in agent_names:
            agent = self._agents.get(name)
            if agent is None:
                steps.append(
                    {
                        "agent": name,
                        "task": current_task,
                        "output": "",
                        "success": False,
                        "error": f"Agent '{name}' not found.",
                    }
                )
                continue

            result = agent.run(current_task, context)
            steps.append(result)
            self.memory.store(name, result)
            context[name] = result

            # Pass successful output as the task for the next agent
            if result["success"] and result["output"]:
                current_task = result["output"]

        final_output = steps[-1]["output"] if steps else ""
        all_succeeded = all(s["success"] for s in steps)

        return {
            "final_output": final_output,
            "steps": steps,
            "memory": self.memory.get_context(),
            "success": all_succeeded,
        }

    def run_parallel(
        self,
        tasks: List[str],
        agents: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Run multiple tasks concurrently across agents.

        Tasks and agents are paired by index (round-robin if there are more
        tasks than agents).

        Args:
            tasks: List of task strings to execute.
            agents: Agent names to use.  Defaults to all registered agents.

        Returns:
            List of per-task result dicts in the same order as *tasks*.
        """
        agent_names = agents or list(self._agents.keys())
        if not agent_names:
            return [
                {
                    "agent": None,
                    "task": t,
                    "output": "",
                    "success": False,
                    "error": "No agents registered.",
                }
                for t in tasks
            ]

        results: List[Optional[Dict[str, Any]]] = [None] * len(tasks)
        threads: List[threading.Thread] = []

        def _run(index: int, agent: BaseAgent, task: str) -> None:
            context = self.memory.get_context()
            result = agent.run(task, context)
            results[index] = result
            self.memory.store(f"{agent.name}_{index}", result)

        for i, task in enumerate(tasks):
            agent_name = agent_names[i % len(agent_names)]
            agent = self._agents.get(agent_name)
            if agent is None:
                results[i] = {
                    "agent": agent_name,
                    "task": task,
                    "output": "",
                    "success": False,
                    "error": f"Agent '{agent_name}' not found.",
                }
                continue
            thread = threading.Thread(
                target=_run, args=(i, agent, task), daemon=True
            )
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        return [r for r in results if r is not None]

    def route(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Automatically route *task* to the best-matched agent.

        Scoring is based on how many words from *task* appear in the
        agent's role description (case-insensitive).  Falls back to the
        first registered agent when no keywords match.

        Args:
            task: Task string to route.
            context: Optional shared context dict.

        Returns:
            The selected agent's result dict, with an additional
            ``"routed_to"`` key naming the chosen agent.

        Raises:
            RuntimeError: If no agents are registered.
        """
        if not self._agents:
            raise RuntimeError("No agents are registered in the orchestrator.")

        best_agent: Optional[BaseAgent] = None
        best_score = -1

        task_words = set(task.lower().split())

        for agent in self._agents.values():
            role_words = set(agent.role.lower().split())
            score = len(task_words & role_words)
            if score > best_score:
                best_score = score
                best_agent = agent

        if best_agent is None:
            best_agent = next(iter(self._agents.values()))

        ctx = context or self.memory.get_context()
        result = best_agent.run(task, ctx)
        result["routed_to"] = best_agent.name
        self.memory.store(f"routed_{best_agent.name}", result)
        return result

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    def reset_memory(self) -> None:
        """Clear all shared memory."""
        self.memory.clear()

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"Orchestrator(agents={list(self._agents.keys())}, "
            f"memory_keys={self.memory.keys()})"
        )
