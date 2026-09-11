"""Sequential and parallel pipeline execution for RealAI agents.

A :class:`Pipeline` chains a series of (agent, task_fn) steps where each
step's output is forwarded as input to the next task function.

Example::

    from realai import RealAIClient
    from realai_orchestration.agent import BaseAgent
    from realai_orchestration.pipeline import Pipeline

    client = RealAIClient()

    researcher = BaseAgent("researcher", "Research the topic.", client)
    writer = BaseAgent("writer", "Write a summary.", client)

    pipe = Pipeline([
        (researcher, lambda _inp: "Research quantum computing trends"),
        (writer, lambda inp: f"Write a blog post using: {inp}"),
    ])

    result = pipe.run("quantum computing")
"""

from typing import Any, Callable, Dict, List, Optional, Tuple

from .agent import BaseAgent
from .memory import SharedMemory


# Type alias: each step is a (BaseAgent, task_fn) pair where task_fn
# takes the previous step's output and returns a task string.
Step = Tuple[BaseAgent, Callable[[Any], str]]


class Pipeline:
    """Executes a fixed sequence of agent steps.

    Each step receives the output of the previous step (or *initial_input*
    for the first step) via a *task_fn* that transforms it into a task string.

    Args:
        steps: List of ``(agent, task_fn)`` tuples.
        memory: Optional :class:`~memory.SharedMemory`.  A fresh instance is
            created automatically when not provided.
        stop_on_failure: When True (default), abort remaining steps if any
            step fails.  When False, the pipeline continues using the last
            successful output.

    Example::

        def first_task(_):
            return "Summarize the latest AI news."

        def second_task(prev_output):
            return f"Translate to French: {prev_output}"

        pipe = Pipeline([(summariser_agent, first_task), (translator_agent, second_task)])
        result = pipe.run(None)
    """

    def __init__(
        self,
        steps: List[Step],
        memory: Optional[SharedMemory] = None,
        stop_on_failure: bool = True,
    ) -> None:
        if not steps:
            raise ValueError("Pipeline must have at least one step.")
        self.steps = steps
        self.memory: SharedMemory = memory or SharedMemory()
        self.stop_on_failure = stop_on_failure

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self, initial_input: Any) -> Dict[str, Any]:
        """Execute all pipeline steps sequentially.

        Args:
            initial_input: Seed value passed to the first step's task_fn.

        Returns:
            Dict with:
                - ``final_output``: The last successful agent output.
                - ``steps``: List of per-step result dicts.
                - ``memory``: Final shared memory snapshot.
                - ``success``: True if all steps succeeded.
                - ``failed_step``: Index of the first failed step, or None.
        """
        step_results: List[Dict[str, Any]] = []
        current_input: Any = initial_input
        failed_step: Optional[int] = None

        for i, (agent, task_fn) in enumerate(self.steps):
            try:
                task = task_fn(current_input)
            except Exception as exc:  # noqa: BLE001
                result: Dict[str, Any] = {
                    "agent": agent.name,
                    "task": str(current_input),
                    "output": "",
                    "success": False,
                    "error": f"task_fn raised: {exc}",
                    "step": i,
                }
                step_results.append(result)
                if failed_step is None:
                    failed_step = i
                if self.stop_on_failure:
                    break
                continue

            context = self.memory.get_context()
            result = agent.run(task, context)
            result["step"] = i
            step_results.append(result)
            self.memory.store(f"step_{i}_{agent.name}", result)

            if result["success"] and result["output"]:
                current_input = result["output"]
            else:
                if failed_step is None:
                    failed_step = i
                if self.stop_on_failure:
                    break

        final_output = ""
        for r in reversed(step_results):
            if r.get("success") and r.get("output"):
                final_output = r["output"]
                break

        return {
            "final_output": final_output,
            "steps": step_results,
            "memory": self.memory.get_context(),
            "success": failed_step is None,
            "failed_step": failed_step,
        }

    def add_step(self, agent: BaseAgent, task_fn: Callable[[Any], str]) -> None:
        """Append a step to the end of the pipeline.

        Args:
            agent: Agent to execute.
            task_fn: Callable that converts the previous output to a task string.
        """
        self.steps.append((agent, task_fn))

    def __len__(self) -> int:
        return len(self.steps)

    def __repr__(self) -> str:  # pragma: no cover
        names = [a.name for a, _ in self.steps]
        return f"Pipeline(steps={names})"
