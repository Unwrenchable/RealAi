"""RealAI Memory subsystem."""
from __future__ import annotations

from .engine import MemoryEngine

try:
    from .sqlite_memory import get_conn, init_db
except Exception:  # pragma: no cover
    get_conn = None  # type: ignore
    init_db = None  # type: ignore

try:
    from .fabric import (
        MemoryRecord,
        fabric_path,
        memory_fabric_status,
        purge_expired,
        read_memory,
        write_memory,
    )
except Exception:  # pragma: no cover
    MemoryRecord = None  # type: ignore
    fabric_path = None  # type: ignore
    memory_fabric_status = None  # type: ignore
    purge_expired = None  # type: ignore
    read_memory = None  # type: ignore
    write_memory = None  # type: ignore

__all__ = [
    "MemoryEngine",
    "get_conn",
    "init_db",
    "MemoryRecord",
    "fabric_path",
    "write_memory",
    "read_memory",
    "purge_expired",
    "memory_fabric_status",
]
