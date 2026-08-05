from typing import List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    max_tokens: Optional[int] = Field(default=None, alias="max_tokens")
    temperature: Optional[float] = None
    stream: Optional[bool] = False

    class Config:
        allow_population_by_field_name = True
        extra = "ignore"
