"""Shared memory and state management for multi-agent orchestration."""

import threading
from typing import Any, Dict, List, Optional


class SharedMemory:
    """Thread-safe key-value store shared across agents in an orchestration.

    Agents read and write named slots; the full context dict is passed into
    each agent run so downstream agents can build on upstream results.

    Example::

        mem = SharedMemory()
        mem.store("research", {"topic": "AI trends"})
        ctx = mem.get_context()  # {"research": {"topic": "AI trends"}}
    """

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._history: List[Dict[str, Any]] = []

    def store(self, key: str, value: Any) -> None:
        """Store a value under *key*.

        Args:
            key: Identifier for the stored value.
            value: Any serializable Python object.
        """
        with self._lock:
            self._store[key] = value
            self._history.append({"action": "store", "key": key})

    def retrieve(self, key: str, default: Any = None) -> Any:
        """Retrieve the value stored under *key*.

        Args:
            key: Identifier to look up.
            default: Value returned when the key is absent. Defaults to None.

        Returns:
            The stored value, or *default* if the key does not exist.
        """
        with self._lock:
            return self._store.get(key, default)

    def get_context(self) -> Dict[str, Any]:
        """Return a shallow copy of the entire memory store.

        Returns:
            Mapping of all stored key-value pairs.
        """
        with self._lock:
            return dict(self._store)

    def clear(self) -> None:
        """Remove all stored values and reset history."""
        with self._lock:
            self._store.clear()
            self._history.clear()

    def keys(self) -> List[str]:
        """Return all stored keys.

        Returns:
            List of key names currently in the store.
        """
        with self._lock:
            return list(self._store.keys())

    def delete(self, key: str) -> bool:
        """Delete a single key.

        Args:
            key: Key to remove.

        Returns:
            True if the key existed and was deleted, False otherwise.
        """
        with self._lock:
            if key in self._store:
                del self._store[key]
                self._history.append({"action": "delete", "key": key})
                return True
            return False

    def get_history(self) -> List[Dict[str, Any]]:
        """Return a copy of the operation history.

        Returns:
            List of dicts describing past store/delete operations.
        """
        with self._lock:
            return list(self._history)

    def __repr__(self) -> str:  # pragma: no cover
        with self._lock:
            return f"SharedMemory(keys={list(self._store.keys())})"
