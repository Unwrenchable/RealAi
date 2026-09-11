"""Unified memory package.

``core.memory`` used to be a single JSON engine module, which broke
``from core.memory.sqlite_store import …``. This package re-exports
sqlite / chroma / long-term adapters and keeps ``MemoryEngine`` for
legacy orchestrator imports.
"""

from .json_engine import MemoryEngine
from .sqlite_store import SQLiteMemoryStore
from .summarizer import ConversationSummarizer

try:
    from .bridge import load_long_term_engine, memory_capabilities
except Exception:  # pragma: no cover
    load_long_term_engine = None  # type: ignore
    memory_capabilities = lambda: {"core_sqlite": True}  # type: ignore

__all__ = [
    "MemoryEngine",
    "SQLiteMemoryStore",
    "ConversationSummarizer",
    "load_long_term_engine",
    "memory_capabilities",
]
