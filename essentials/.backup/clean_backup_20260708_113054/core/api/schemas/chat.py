"""Chat completion schemas."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    tools: Optional[List[Dict[str, Any]]] = None
    user_id: Optional[str] = "default-user"


class ChatCompletionResponse(BaseModel):
    id: str
    model: str
    choices: List[Dict[str, Any]]
