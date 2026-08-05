"""OpenTelemetry tracer with fallback."""

from contextlib import contextmanager

try:
    from opentelemetry import trace
except ImportError:  # pragma: no cover
    trace = None


if trace is None:  # pragma: no cover
    class _NoopTracer:
        @contextmanager
        def start_as_current_span(self, _name: str):
            yield

    tracer = _NoopTracer()
else:
    tracer = trace.get_tracer("realai")

