import time
import uuid
from typing import List

from . import config
from .schemas import ChatCompletionRequest, ChatMessage


class MockProvider:
    """Simple echo-style provider used as the default engine."""

    def __init__(self, model_id: str, owned_by: str = config.DEFAULT_MODEL_OWNER):
        self.model_id = model_id
        self.owned_by = owned_by

    def available_models(self) -> List[dict]:
        now = int(time.time())
        return config.get_default_models(now)

    def chat_completion(self, request: ChatCompletionRequest) -> dict:
        created = int(time.time())
        content = self._build_reply(request.messages)
        prompt_tokens = self._count_tokens(request.messages)
        completion_tokens = self._count_tokens_text(content)

        return {
            "id": f"chatcmpl-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": created,
            "model": request.model or self.model_id,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }

    def _build_reply(self, messages: List[ChatMessage]) -> str:
        user_messages = [m.content for m in messages if m.role == "user"]
        if user_messages:
            return f"Echo: {user_messages[-1]}"
        return "Echo: ready whenever you are."

    def _count_tokens(self, messages: List[ChatMessage]) -> int:
        return sum(self._count_tokens_text(message.content) for message in messages)

    @staticmethod
    def _count_tokens_text(text: str) -> int:
        return len(text.split())


class ProviderRouter:
    """Lightweight router placeholder. For now, everything goes to MockProvider."""

    def __init__(self, default_provider: MockProvider):
        self.default_provider = default_provider

    def route_chat(self, request: ChatCompletionRequest) -> dict:
        # Future: inspect request.model and pick provider
        return self.default_provider.chat_completion(request)

    def list_models(self) -> List[dict]:
        return self.default_provider.available_models()
