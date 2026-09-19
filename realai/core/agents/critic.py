"""Critic agent."""

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


class CriticAgent(Agent):
    name = "critic"

    def __init__(self, inference: InferenceRegistry):
        self.inference = inference

    def step(self, messages, context):
        with tracer.start_as_current_span("agent.critique"):
            backend = self.inference.get_chat(context["model"])
            critique = backend.generate([
                {"role": "system", "content": "You are a critic. Evaluate the result quality and gaps."},
                *[message.dict() if hasattr(message, "dict") else message for message in messages],
                {"role": "user", "content": "Critique the latest result in one short paragraph."},
            ])
            result = {"critique": critique["choices"][0]["message"].get("content", "")}
            log("agent.critique", result)
            return result
