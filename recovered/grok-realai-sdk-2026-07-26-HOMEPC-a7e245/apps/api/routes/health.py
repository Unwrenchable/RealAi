"""Health and readiness probes."""

from fastapi import APIRouter

from apps.api.state import model_cache

router = APIRouter()


@router.get("/healthz")
def health():
    return {"status": "ok"}


@router.get("/readyz")
def ready():
    return {"models_loaded": "registry" in model_cache.loaded}

