"""Planner agent."""

import json

from core.agents.base import Agent, AgentContext
from core.inference.registry import InferenceRegistry
from core.logging.logger import log
from core.tracing.tracer import tracer


class PlannerAgent(Agent):
    name = "planner"

    def __init__(self, inference: InferenceRegistry):
        self.inference = inference

    def step(self, messages, context):
        with tracer.start_as_current_span("agent.plan"):
            backend = self.inference.get_chat(context["model"])
            plan = backend.generate([
                {"role": "system", "content": "You are a planning agent. Return JSON list of steps."},
                *[message.dict() if hasattr(message, "dict") else message for message in messages],
                {"role": "user", "content": "Break the task into clear steps."},
            ])
            content = plan["choices"][0]["message"].get("content", "")
            steps = _parse_steps(content)
            if not steps:
                steps = ["Analyze task", "Execute key step", "Summarize result"]
            log("agent.plan", {"plan": steps})
            return {"plan": steps}


def _parse_steps(content: str):
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except Exception:
        pass
    lines = [line.strip("- ").strip() for line in content.splitlines() if line.strip()]
    return [line for line in lines if line]
