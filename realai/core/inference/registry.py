"""Inference backend registry."""

from typing import Dict

from core.inference.backend import ChatBackend, EmbeddingsBackend


class InferenceRegistry:
    def __init__(self):
        self.chat_backends: Dict[str, ChatBackend] = {}
        self.embed_backends: Dict[str, EmbeddingsBackend] = {}

    def register_chat(self, model_id: str, backend: ChatBackend):
        self.chat_backends[model_id] = backend

    def register_embed(self, model_id: str, backend: EmbeddingsBackend):
        self.embed_backends[model_id] = backend

    def get_chat(self, model_id: str) -> ChatBackend:
        if model_id not in self.chat_backends:
            raise KeyError("Unknown chat model: {0}".format(model_id))
        return self.chat_backends[model_id]

    def get_embed(self, model_id: str) -> EmbeddingsBackend:
        if model_id not in self.embed_backends:
            raise KeyError("Unknown embedding model: {0}".format(model_id))
        return self.embed_backends[model_id]

