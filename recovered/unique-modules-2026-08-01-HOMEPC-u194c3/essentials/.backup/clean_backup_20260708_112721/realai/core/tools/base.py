from typing import Any, Dict, List, Protocol


class Tool(Protocol):
    name: str
    description: str
    params_schema: Dict[str, Any]
    permissions: List[str]

    def __call__(self, **kwargs: Any) -> Any:
        ...
