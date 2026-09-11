"""Task graph executor (planner -> worker -> critic -> synthesizer)."""

from typing import Any, Dict, List

from core.agents.safety import AgentSafety
from core.logging.logger import log
from core.tracing.tracer import tracer


class TaskExecutor:
    def __init__(self, planner, worker, critic, synthesizer, safety: AgentSafety = None):
        self.planner = planner
        self.worker = worker
        self.critic = critic
        self.synthesizer = synthesizer
        self.safety = safety or AgentSafety()

    def run(self, messages, context):
        with tracer.start_as_current_span("agent.execute"):
            plan_data = self.planner.step(messages, context)
            steps = plan_data.get("plan", [])
            if not isinstance(steps, list):
                steps = [str(steps)]
            context["plan"] = steps

            results: List[Dict[str, Any]] = []
            for index, step in enumerate(steps, start=1):
                self.safety.validate_step(index)
                log("agent.step", {"step": step, "index": index})
                context["current_step"] = step
                worker_out = self.worker.step(messages, context)
                results.append({"step": step, "worker": worker_out})

                context["worker_output"] = worker_out
                critique = self.critic.step(messages, context)
                results.append({"step": step, "critique": critique})

            context["results"] = results
            final = self.synthesizer.step(messages, context)
            return {
                "plan": steps,
                "results": results,
                "final": final.get("final", ""),
            }
