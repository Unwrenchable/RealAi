"""Base Web3 backend protocol."""

from typing import Any, Dict, Protocol


class Web3Backend(Protocol):
    name: str

    def get_account(self, address: str) -> Dict[str, Any]:
        ...

    def simulate(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        ...

    def send(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        ...

    def call(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        ...

