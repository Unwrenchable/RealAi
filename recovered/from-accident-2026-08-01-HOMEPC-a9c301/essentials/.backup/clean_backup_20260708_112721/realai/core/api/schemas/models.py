"""Model registry schemas."""

from typing import List, Optional

from pydantic import BaseModel


class ModelInfo(BaseModel):
    id: str
    type: Optional[str] = None
    backend: Optional[str] = None


class ModelsListResponse(BaseModel):
    data: List[ModelInfo]

