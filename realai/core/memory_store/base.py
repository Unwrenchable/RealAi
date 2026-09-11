from typing import Any, Dict, List, Protocol


class MemoryStore(Protocol):
    def add(self, user_id: str, items: List[Dict[str, Any]]) -> None:
        ...

    def search(self, user_id: str, query: str, k: int = 5) -> List[Dict[str, Any]]:
        ...

    def clear(self, user_id: str) -> None:
        ...

