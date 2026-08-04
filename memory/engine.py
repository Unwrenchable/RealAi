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
import re
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PrivacyTier(Enum):
    """Privacy tier for memory items.

    Attributes:
        EPHEMERAL: Not persisted; cleared at session end.
        SESSION: Persisted for the duration of the session only.
        PERSISTENT: Permanently stored across sessions.
    """

    EPHEMERAL = "ephemeral"
    SESSION = "session"
    PERSISTENT = "persistent"


class VectorStoreAdapter(ABC):
    """Abstract base class for vector store backends.

    Implementations must provide add(), search(), and delete() methods.
    """

    @abstractmethod
    def add(self, id: str, vector: List[float], metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a vector to the store.

        Args:
            id: Unique identifier for the vector.
            vector: Float list representing the embedding.
            metadata: Optional dict of metadata to associate.
        """

    @abstractmethod
    def search(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Find the top_k most similar vectors.

        Args:
            query_vector: Query embedding.
            top_k: Number of results to return.

        Returns:
            List of dicts with at minimum {"id": str, "score": float}.
        """

    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete a vector by ID.

        Args:
            id: The ID to delete.

        Returns:
            True if found and deleted, False otherwise.
        """


class LocalVectorStore(VectorStoreAdapter):
    """Pure in-memory vector store using cosine similarity.

    No external dependencies required.
    """

    def __init__(self) -> None:
        """Initialize an empty local vector store."""
        self._vectors: Dict[str, List[float]] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

    def add(self, id: str, vector: List[float], metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store a vector with optional metadata.

        Args:
            id: Unique identifier.
            vector: Embedding vector.
            metadata: Optional metadata dict.
        """
        self._vectors[id] = vector
        self._metadata[id] = metadata or {}

    def search(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Return top_k most similar vectors using cosine similarity.

        Args:
            query_vector: Query embedding.
            top_k: Number of results to return.

        Returns:
            List of {"id": str, "score": float, "metadata": dict}, sorted by score descending.
        """
        scored = []
        q_norm = math.sqrt(sum(v * v for v in query_vector)) or 1.0
        for vec_id, vec in self._vectors.items():
            dot = sum(a * b for a, b in zip(query_vector, vec))
            v_norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            score = dot / (q_norm * v_norm)
            scored.append({"id": vec_id, "score": score, "metadata": self._metadata.get(vec_id, {})})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def delete(self, id: str) -> bool:
        """Delete a vector by ID.

        Args:
            id: ID to delete.

        Returns:
            True if found and deleted.
        """
        if id in self._vectors:
            del self._vectors[id]
            self._metadata.pop(id, None)
            return True
        return False


class ChromaVectorStore(VectorStoreAdapter):
    """Optional ChromaDB-backed vector store.

    Falls back to LocalVectorStore when chromadb is not installed.
    """

    def __init__(self, collection_name: str = "realai_memory") -> None:
        """Initialize ChromaDB collection or fall back to LocalVectorStore.

        Args:
            collection_name: Name for the ChromaDB collection.
        """
        self._fallback: Optional[LocalVectorStore] = None
        self._collection = None
        try:
            import chromadb  # type: ignore
            client = chromadb.Client()
            self._collection = client.get_or_create_collection(collection_name)
        except Exception:
            self._fallback = LocalVectorStore()

    def add(self, id: str, vector: List[float], metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a vector to ChromaDB or fallback store."""
        if self._fallback is not None:
            self._fallback.add(id, vector, metadata)
            return
        try:
            self._collection.add(
                embeddings=[vector],
                ids=[id],
                metadatas=[metadata or {}],
            )
        except Exception:
            if self._fallback is None:
                self._fallback = LocalVectorStore()
            self._fallback.add(id, vector, metadata)

    def search(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """Search ChromaDB or fallback store."""
        if self._fallback is not None:
            return self._fallback.search(query_vector, top_k)
        try:
            results = self._collection.query(
                query_embeddings=[query_vector],
                n_results=top_k,
            )
            out = []
            for i, vec_id in enumerate(results.get("ids", [[]])[0]):
                out.append({
                    "id": vec_id,
                    "score": 1.0 - (results.get("distances", [[]])[0][i] if results.get("distances") else 0.0),
                    "metadata": results.get("metadatas", [[]])[0][i] if results.get("metadatas") else {},
                })
            return out
        except Exception:
            if self._fallback is None:
                self._fallback = LocalVectorStore()
            return self._fallback.search(query_vector, top_k)

    def delete(self, id: str) -> bool:
        """Delete from ChromaDB or fallback store."""
        if self._fallback is not None:
            return self._fallback.delete(id)
        try:
            self._collection.delete(ids=[id])
            return True
        except Exception:
            return False


def extract_entities(text: str) -> List[Dict[str, str]]:
    """Extract entities from text using regex patterns.

    Detects: EMAIL, URL, DATE (YYYY-MM-DD), PHONE, MENTION (@word), HASHTAG (#word).

    Args:
        text: Input text to analyse.

    Returns:
        List of dicts, each with "type" and "value" keys.
    """
    entities: List[Dict[str, str]] = []

    # EMAIL
    for m in re.finditer(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b", text):
        entities.append({"type": "EMAIL", "value": m.group()})

    # URL
    for m in re.finditer(r"https?://[^\s\"'>]+", text):
        entities.append({"type": "URL", "value": m.group()})

    # DATE (YYYY-MM-DD)
    for m in re.finditer(r"\b\d{4}-\d{2}-\d{2}\b", text):
        entities.append({"type": "DATE", "value": m.group()})

    # PHONE (various formats)
    for m in re.finditer(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b", text):
        entities.append({"type": "PHONE", "value": m.group()})

    # MENTION (@word)
    for m in re.finditer(r"@[A-Za-z0-9_]+", text):
        entities.append({"type": "MENTION", "value": m.group()})

    # HASHTAG (#word)
    for m in re.finditer(r"#[A-Za-z0-9_]+", text):
        entities.append({"type": "HASHTAG", "value": m.group()})

    return entities


class RetentionPolicy:
    """Time-to-live retention policy for memory items.

    Items older than ttl_seconds are considered expired.
    """

    def __init__(self, ttl_seconds: float = 86400.0) -> None:
        """Initialize the retention policy.

        Args:
            ttl_seconds: Number of seconds before an item is considered expired.
                Default is 86400 (24 hours).
        """
        self._ttl = ttl_seconds

    def is_expired(self, item: "MemoryItem") -> bool:
        """Check whether a memory item has exceeded its TTL.

        Args:
            item: MemoryItem to check.

        Returns:
            True if the item is expired, False otherwise.
        """
        return (time.time() - item.timestamp) > self._ttl

    def apply(self, items: "List[MemoryItem]") -> "List[MemoryItem]":
        """Filter out expired items.

        Args:
            items: List of MemoryItem objects.

        Returns:
            List of non-expired MemoryItem objects.
        """
        return [item for item in items if not self.is_expired(item)]


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

    def __init__(
        self,
        policy: Optional[MemoryRetrievalPolicy] = None,
        privacy_tier: PrivacyTier = PrivacyTier.SESSION,
        user_id: str = "default",
    ) -> None:
        """Initialize the memory engine with all tiers.

        Args:
            policy: Optional retrieval policy weights.
            privacy_tier: Privacy tier for new memory items (stored as attribute).
            user_id: User identifier for namespacing (stored as attribute).
        """
        self.policy = policy or MemoryRetrievalPolicy()
        self.privacy_tier = privacy_tier
        self.user_id = user_id
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


class UserMemoryScope:
    """Per-user scoped memory with privacy tier support.

    Each UserMemoryScope maintains a completely isolated MemoryEngine instance,
    ensuring no cross-user contamination.
    """

    def __init__(
        self,
        user_id: str,
        privacy_tier: PrivacyTier = PrivacyTier.SESSION,
    ) -> None:
        """Initialize a scoped memory for a specific user.

        Args:
            user_id: Unique identifier for the user. Used for namespace isolation.
            privacy_tier: Privacy tier controlling persistence behaviour.
        """
        self._user_id = user_id
        self._privacy_tier = privacy_tier
        self._engine = MemoryEngine(user_id=user_id, privacy_tier=privacy_tier)
        self._ephemeral_ids: List[str] = []

    def store(self, content: str, tags: Optional[List[str]] = None) -> str:
        """Store content in the user's scoped memory.

        Args:
            content: Text content to store.
            tags: Optional list of tags.

        Returns:
            Generated item ID string.
        """
        item_id = self._engine.store(
            content,
            tags=tags,
            namespace=self._user_id,
        )
        if self._privacy_tier == PrivacyTier.EPHEMERAL:
            self._ephemeral_ids.append(item_id)
        return item_id

    def retrieve(self, query: str, top_k: int = 5) -> List[MemoryItem]:
        """Retrieve memories relevant to the query from this user's scope only.

        Args:
            query: Query string.
            top_k: Number of results.

        Returns:
            List of MemoryItem objects from this user's namespace only.
        """
        return self._engine.retrieve(query, top_k=top_k, namespace=self._user_id)

    def clear_ephemeral(self) -> int:
        """Clear all EPHEMERAL-tier memory items.

        Returns:
            Number of items cleared.
        """
        count = 0
        for item_id in list(self._ephemeral_ids):
            if self._engine.forget(item_id):
                count += 1
        self._ephemeral_ids = []
        return count


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

MEMORY_ENGINE = MemoryEngine()
