"""Model routes."""

from fastapi import APIRouter

from apps.api.state import model_cache
from core.api.schemas.models import ModelsListResponse
from core.models.registry import ModelRegistry

router = APIRouter()


@router.get("/v1/models", response_model=ModelsListResponse)
def list_models():
    registry = model_cache.get("registry", lambda: ModelRegistry())
    return {"data": registry.list_models()}


@router.post("/v1/models/reload")
def reload_models():
    model_cache.clear()
    return {"status": "reloaded"}
