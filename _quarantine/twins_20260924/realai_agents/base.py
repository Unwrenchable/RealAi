from typing import Any, Dict, List, Protocol


class AgentContext(Dict[str, Any]):
    ...


class Agent(Protocol):
    name: str

    def step(
        self,
        messages: List[Any],
        context: AgentContext,
    ) -> Dict[str, Any]:
        ...
