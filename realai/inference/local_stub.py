"""Local structured stub backends."""

import uuid
from typing import Any, Dict, List

from core.inference.backend import ChatBackend, EmbeddingsBackend


class LocalStubChat(ChatBackend):
    name = "local-stub-chat"

    def generate(self, messages: List[Dict[str, Any]], **kwargs: Any) -> Dict[str, Any]:
        latest = messages[-1] if messages else {}
        content = str(latest.get("content", "")).lower()
        if "search the web for" in content:
            query = content.split("search the web for", 1)[1].strip() or "latest updates"
            return {
                "id": str(uuid.uuid4()),
                "model": self.name,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "",
                            "tool_call": {"name": "web_search", "arguments": {"query": query}},
                        },
                    }
                ],
            }
        if latest.get("role") == "tool":
            return {
                "id": str(uuid.uuid4()),
                "model": self.name,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "I used the tool result and prepared an answer.",
                        },
                    }
                ],
            }
        return {
            "id": str(uuid.uuid4()),
            "model": self.name,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "RealAI local stub backend. Model integration coming next.",
                    },
                }
            ],
        }


class LocalStubEmbeddings(EmbeddingsBackend):
    name = "local-stub-embed"

    def embed(self, texts: List[str], **kwargs: Any) -> Dict[str, Any]:
        return {
            "model": self.name,
            "data": [{"embedding": [0.0] * 10, "index": i} for i, _ in enumerate(texts)],
        }
