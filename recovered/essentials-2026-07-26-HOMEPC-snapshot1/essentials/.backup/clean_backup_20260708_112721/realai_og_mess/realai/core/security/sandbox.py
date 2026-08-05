"""Sandbox protocol for secure code execution."""

from typing import Any, Dict, Protocol


class Sandbox(Protocol):
    def run(self, code: str) -> Dict[str, Any]:
        ...

