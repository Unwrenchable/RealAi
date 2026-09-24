"""Synthesizer agent."""

from core.agents.base import Agent, AgentContext
from core.inference.registry import InferenceRegistry
from core.logging.logger import log
from core.tracing.tracer import tracer


class SynthesizerAgent(Agent):
    name = "synthesizer"

    def __init__(self, inference: InferenceRegistry):
        self.inference = inference

    def step(self, messages, context):
        with tracer.start_as_current_span("agent.synthesis"):
            backend = self.inference.get_chat(context["model"])
            final = backend.generate([
                {"role": "system", "content": "Synthesize all results into a final answer."},
                *[message.dict() if hasattr(message, "dict") else message for message in messages],
                {"role": "user", "content": "Return concise final output with actions taken."},
            ])
            result = {"final": final["choices"][0]["message"].get("content", "")}
            log("agent.synthesis", result)
            return result
