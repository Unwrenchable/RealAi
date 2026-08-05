"""
RealAI Memory Engine
=====================
Multi-tier memory system: short-term, episodic, symbolic, and semantic.

Usage::

    from realai.memory.engine import MEMORY_ENGINE

    item_id = MEMORY_ENGINE.store("The sky is blue", tags=["fact"])
    results = MEMORY_ENGINE.retrieve("sky color")
"""

from __future__ import annotations

import hashlib
import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MemoryItem:
    """A single memory item.

    Attributes:
        id: Unique identifier.
        content: Text content of the memory.
        timestamp: Unix creation timestamp.
        score: Relevance or quality score (0.0-1.0).
        tags: List of category tags.
        namespace: Memory namespace for isolation.
    """

    id: str
    content: str
    timestamp: float
    score: float = 1.0
    tags: List[str] = field(default_factory=list)
    namespace: str = "default"


class ShortTermMemory:
    """Fixed-capacity FIFO short-term memory.

    Evicts oldest items when capacity is exceeded.
    """

    def __init__(self, capacity: int = 20) -> None:
        """Initialize short-term memory.

        Args:
            capacity: Maximum number of items to store.
        """
        self._capacity = capacity
        self._items: List[MemoryItem] = []

    def add(self, item: MemoryItem) -> None:
        """Add an item, evicting oldest if over capacity.

        Args:
            item: MemoryItem to add.
        """
        self._items.append(item)
        if len(self._items) > self._capacity:
            self._items = self._items[-self._capacity:]

    def get_recent(self, n: int = 10) -> List[MemoryItem]:
        """Return the n most recent items.

        Args:
            n: Number of items to return.

        Returns:
            List of MemoryItem, most recent last.
        """
        return self._items[-n:]

    def clear(self) -> None:
        """Clear all items."""
        self._items = []


class EpisodicMemory:
    """Time-decayed episodic memory.

    Scores decay exponentially based on item age.
    """

    def __init__(self, decay_factor: float = 0.95) -> None:
        """Initialize episodic memory.

        Args:
            decay_factor: Daily decay multiplier (0.0-1.0).
        """
        self._decay_factor = decay_factor
        self._items: List[MemoryItem] = []

    def add(self, item: MemoryItem) -> None:
        """Add an item to episodic memory.

        Args:
            item: MemoryItem to store.
        """
        self._items.append(item)

    def get_score(self, item: MemoryItem) -> float:
        """Calculate the current decayed score for an item.

        Args:
            item: The MemoryItem to score.

        Returns:
            Decayed score: item.score * (decay_factor ** days_since_creation).
        """
        days = (time.time() - item.timestamp) / 86400.0
        return item.score * (self._decay_factor ** days)

    def retrieve(self, query: str, top_k: int = 5) -> List[MemoryItem]:
        """Retrieve top_k items sorted by decayed score.

        Args:
            query: Query string (used for future semantic ranking).
            top_k: Number of items to return.

        Returns:
            Top-k MemoryItems sorted by descending decayed score.
        """
        scored = [(self.get_score(item), item) for item in self._items]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    def all(self) -> List[MemoryItem]:
        """Return all episodic memory items.

        Returns:
            List of all MemoryItem objects.
        """
        return list(self._items)


class SymbolicMemory:
    """Key-value symbolic fact store with confidence and contradiction detection.

    Supports namespaced facts with confidence levels.
    """

    def __init__(self) -> None:
        """Initialize an empty symbolic memory."""
        # Keyed as (namespace, key) -> {"value": ..., "confidence": float}
        self._facts: Dict[tuple, Dict[str, Any]] = {}

    def assert_fact(
        self,
        key: str,
        value: Any,
        confidence: float = 1.0,
        namespace: str = "default",
    ) -> None:
        """Store a fact with the given key and confidence.

        Args:
            key: Fact key string.
            value: Fact value (any serializable type).
            confidence: Confidence level (0.0-1.0).
            namespace: Namespace for the fact.
        """
        self._facts[(namespace, key)] = {"value": value, "confidence": confidence}

    def retract_fact(self, key: str, namespace: str = "default") -> bool:
        """Remove a fact.

        Args:
            key: Fact key to remove.
            namespace: Namespace for the fact.

        Returns:
            True if the fact was found and removed, False otherwise.
        """
        fact_key = (namespace, key)
        if fact_key in self._facts:
            del self._facts[fact_key]
            return True
        return False

    def query(self, key: str, namespace: str = "default") -> Optional[Dict[str, Any]]:
        """Look up a fact.

        Args:
            key: Fact key to look up.
            namespace: Namespace to search.

        Returns:
            Dict with "value" and "confidence" keys, or None if not found.
        """
        return self._facts.get((namespace, key))

    def detect_contradiction(
        self,
        key: str,
        new_value: Any,
        namespace: str = "default",
    ) -> bool:
        """Check if a new value contradicts an existing fact.

        Args:
            key: Fact key to check.
            new_value: New value to compare against existing.
            namespace: Namespace for the fact.

        Returns:
            True if existing fact has a different value.
        """
        existing = self._facts.get((namespace, key))
        if existing is None:
            return False
        return existing["value"] != new_value

    def all_facts(self, namespace: str = "default") -> Dict[str, Any]:
        """Return all facts in a namespace.

        Args:
            namespace: Namespace to query.

        Returns:
            Dict mapping key -> {"value": ..., "confidence": ...}.
        """
        return {
            k: v
            for (ns, k), v in self._facts.items()
            if ns == namespace
        }


class SemanticMemory:
    """Vector-based semantic memory using LocalVectorDB.

    Stores memory items with associated embeddings for similarity search.
    """

    _VECTOR_DIM = 128

    def __init__(self) -> None:
        """Initialize semantic memory with an internal LocalVectorDB."""
        from realai.local_runtime import LocalVectorDB
        self._db = LocalVectorDB()
        self._items: Dict[str, MemoryItem] = {}

    def store(self, item: MemoryItem, vector: Optional[List[float]] = None) -> None:
        """Store a memory item with an optional embedding vector.

        Args:
            item: MemoryItem to store.
            vector: Optional float vector. If None, a hash-based pseudo-vector is used.
        """
        if vector is None:
            vector = self._pseudo_vector(item.content)
        self._db.add(item.id, vector, {"namespace": item.namespace})
        self._items[item.id] = item

    def search(self, query: str, top_k: int = 5) -> List[MemoryItem]:
        """Search for semantically similar memory items.

        Args:
            query: Query string.
            top_k: Number of results to return.

        Returns:
            List of MemoryItem sorted by semantic similarity.
        """
        query_vector = self._pseudo_vector(query)
        hits = self._db.search(query_vector, top_k=top_k)
        results = []
        for hit in hits:
            item = self._items.get(hit["id"])
            if item:
                results.append(item)
        return results

    def _pseudo_vector(self, text: str) -> List[float]:
        """Create a deterministic hash-based pseudo-vector.

        Args:
            text: Input string.

        Returns:
            Normalized float vector of length _VECTOR_DIM.
        """
        digest = hashlib.sha256(text.encode()).hexdigest()
        values = []
        for i in range(0, len(digest), 2):
            byte_val = int(digest[i:i + 2], 16)
            values.append((byte_val - 128) / 128.0)
        # Pad
        while len(values) < self._VECTOR_DIM:
            extra = hashlib.md5((text + str(len(values))).encode()).hexdigest()
            for j in range(0, len(extra), 2):
                byte_val = int(extra[j:j + 2], 16)
                values.append((byte_val - 128) / 128.0)
                if len(values) >= self._VECTOR_DIM:
                    break
        vector = values[:self._VECTOR_DIM]
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]


@dataclass
class MemoryRetrievalPolicy:
    """Weights for multi-tier memory retrieval.

    Attributes:
        recency_weight: Weight for recency (short-term/episodic).
        relevance_weight: Weight for semantic similarity.
        confidence_weight: Weight for symbolic confidence.
    """

    recency_weight: float = 0.4
    relevance_weight: float = 0.4
    confidence_weight: float = 0.2


class MemoryEngine:
    """Multi-tier memory orchestrator.

    Coordinates short-term, episodic, symbolic, and semantic memory tiers.
    """

    def __init__(self, policy: Optional[MemoryRetrievalPolicy] = None) -> None:
        """Initialize the memory engine with all tiers.

        Args:
            policy: Optional retrieval policy weights.
        """
        self.policy = policy or MemoryRetrievalPolicy()
        self.short_term = ShortTermMemory()
        self.episodic = EpisodicMemory()
        self.symbolic = SymbolicMemory()
        self.semantic = SemanticMemory()

    def store(
        self,
        content: str,
        tags: Optional[List[str]] = None,
        namespace: str = "default",
    ) -> str:
        """Store content in all memory tiers.

        Args:
            content: Text content to store.
            tags: Optional list of tags.
            namespace: Memory namespace.

        Returns:
            Generated item ID string.
        """
        item_id = str(uuid.uuid4())
        item = MemoryItem(
            id=item_id,
            content=content,
            timestamp=time.time(),
            score=1.0,
            tags=tags or [],
            namespace=namespace,
        )
        self.short_term.add(item)
        self.episodic.add(item)
        self.semantic.store(item)
        return item_id

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        namespace: str = "default",
    ) -> List[MemoryItem]:
        """Retrieve relevant memories across all tiers.

        Args:
            query: Query string.
            top_k: Number of results to return.
            namespace: Namespace to search.

        Returns:
            Deduplicated list of MemoryItems ranked by combined policy.
        """
        seen_ids = set()
        results = []

        # Semantic search
        semantic_hits = self.semantic.search(query, top_k=top_k)
        for item in semantic_hits:
            if item.id not in seen_ids and item.namespace == namespace:
                seen_ids.add(item.id)
                results.append(item)

        # Fill from episodic if needed
        if len(results) < top_k:
            episodic_hits = self.episodic.retrieve(query, top_k=top_k)
            for item in episodic_hits:
                if item.id not in seen_ids and item.namespace == namespace:
                    seen_ids.add(item.id)
                    results.append(item)
                    if len(results) >= top_k:
                        break

        return results[:top_k]

    def forget(self, item_id: str) -> bool:
        """Remove an item from all memory tiers.

        Args:
            item_id: ID of the item to remove.

        Returns:
            True if found and removed from at least one tier.
        """
        removed = False

        # Remove from short-term
        original_len = len(self.short_term._items)
        self.short_term._items = [
            i for i in self.short_term._items if i.id != item_id
        ]
        if len(self.short_term._items) < original_len:
            removed = True

        # Remove from episodic
        original_len = len(self.episodic._items)
        self.episodic._items = [
            i for i in self.episodic._items if i.id != item_id
        ]
        if len(self.episodic._items) < original_len:
            removed = True

        # Remove from semantic
        if self.semantic._db.delete(item_id):
            removed = True
        if item_id in self.semantic._items:
            del self.semantic._items[item_id]
            removed = True

        return removed


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

MEMORY_ENGINE = MemoryEngine()
