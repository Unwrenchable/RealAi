"""Stubbed model backends for week-1 provider endpoints."""

import uuid
from typing import Any, Dict, List


def stub_chat_completion(messages: List[Dict[str, Any]]):
    return {
        "id": str(uuid.uuid4()),
        "model": "realai-stub",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "RealAI stub response. Local model not yet connected.",
                },
                "finish_reason": "stop",
            }
        ],
    }


def stub_embeddings(texts: List[str]):
    return {
        "model": "realai-embed-stub",
        "data": [{"embedding": [0.0] * 10, "index": i} for i, _ in enumerate(texts)],
    }

