"""Embeddings schemas."""

from typing import List

from pydantic import BaseModel


class EmbeddingsRequest(BaseModel):
    model: str
    input: List[str]


class EmbeddingsResponse(BaseModel):
    data: List[dict]
    model: str

