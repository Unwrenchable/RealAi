from typing import Any, Dict, List, Protocol


class ChatMessage(Dict[str, Any]):
    ...


class ChatCompletion(Protocol):
    id: str
    model: str
    messages: List[ChatMessage]


class ChatModel(Protocol):
    name: str

    def generate(
        self,
        messages: List[ChatMessage],
        tools: List["Tool"] | None = None,
        **kwargs: Any,
    ) -> ChatCompletion:
        ...

