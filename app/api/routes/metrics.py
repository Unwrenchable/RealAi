"""Prometheus metrics endpoint."""

from fastapi import APIRouter, Response

try:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
except ImportError:  # pragma: no cover
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"

    def generate_latest():
        return b""

router = APIRouter()


@router.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

