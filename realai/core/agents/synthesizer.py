"""Synthesizer agent."""

from .base import Agent, AgentContext

try:
    from core.inference.registry import InferenceRegistry  # type: ignore
except Exception:  # pragma: no cover
    InferenceRegistry = object  # type: ignore
try:
    from core.logging.logger import log  # type: ignore
except Exception:  # pragma: no cover
    log = None  # type: ignore
try:
    from core.tracing.tracer import tracer  # type: ignore
except Exception:  # pragma: no cover
    from contextlib import nullcontext

    class _Tracer:
        def start_as_current_span(self, *_a, **_k):
            return nullcontext()

    tracer = _Tracer()  # type: ignore


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
