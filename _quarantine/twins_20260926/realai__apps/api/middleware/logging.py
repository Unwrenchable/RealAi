"""Request/response logging middleware."""

from starlette.middleware.base import BaseHTTPMiddleware

from core.logging.logger import log
from core.metrics.metrics import REQUEST_COUNT, REQUEST_LATENCY
from core.tracing.tracer import tracer


class RequestLogger(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        log("api.request", {"path": path, "method": request.method})
        REQUEST_COUNT.labels(path=path).inc()
        with REQUEST_LATENCY.labels(path=path).time():
            with tracer.start_as_current_span("api.request"):
                response = await call_next(request)
        log("api.response", {"path": path, "status": response.status_code})
        return response

