"""Prometheus metrics with graceful fallback."""

from contextlib import contextmanager

try:
    from prometheus_client import Counter, Histogram
except ImportError:  # pragma: no cover
    class _NoopMetric:
        def labels(self, **_kwargs):
            return self

        def inc(self, _value: float = 1.0):
            return None

        @contextmanager
        def time(self):
            yield

    def Counter(*_args, **_kwargs):  # type: ignore
        return _NoopMetric()

    def Histogram(*_args, **_kwargs):  # type: ignore
        return _NoopMetric()


REQUEST_COUNT = Counter("realai_requests_total", "Total API requests", ["path"])
REQUEST_LATENCY = Histogram("realai_request_latency_seconds", "Request latency", ["path"])
AGENT_STEPS = Counter("realai_agent_steps_total", "Agent steps executed")
TOOL_CALLS = Counter("realai_tool_calls_total", "Tool calls", ["tool"])

