"""Memory adapter — core.memory + recovered long-term engines."""
from __future__ import annotations
from typing import Any

def get_memory_stack() -> dict[str, Any]:
    stack: dict[str, Any] = {"core": ["base", "sqlite_store", "summarizer"]}
    try:
        from core.memory.bridge import memory_capabilities, load_long_term_engine
        stack["capabilities"] = memory_capabilities()
        stack["long_term_engine"] = load_long_term_engine() is not None
    except Exception as e:
        stack["error"] = str(e)
    return stack
