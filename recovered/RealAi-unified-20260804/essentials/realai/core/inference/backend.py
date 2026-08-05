"""Core inference backend protocols."""

from typing import Any, Dict, List, Protocol


class ChatBackend(Protocol):
    name: str

    def generate(
        self,
        messages: List[Dict[str, Any]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        ...


class EmbeddingsBackend(Protocol):
    name: str

    def embed(
        self,
        texts: List[str],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        ...

