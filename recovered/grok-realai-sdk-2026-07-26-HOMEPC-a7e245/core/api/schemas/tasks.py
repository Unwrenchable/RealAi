"""Task API schemas."""

from typing import Any, Dict, List

from pydantic import BaseModel

from core.api.schemas.chat import ChatMessage


class TaskRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    context: Dict[str, Any] = {}


class TaskResponse(BaseModel):
    result: Dict[str, Any]

