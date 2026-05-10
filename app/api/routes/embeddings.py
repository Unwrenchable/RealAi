"""Embeddings routes."""

from fastapi import APIRouter

from apps.api.state import inference_registry
from core.api.schemas.embeddings import EmbeddingsRequest, EmbeddingsResponse

router = APIRouter()


@router.post("/v1/embeddings", response_model=EmbeddingsResponse)
def embeddings(req: EmbeddingsRequest):
    backend = inference_registry.get_embed(req.model)
    return backend.embed(req.input)
