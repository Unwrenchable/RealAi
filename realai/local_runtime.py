"""
RealAI Local Runtime
====================
Provides local model caching, embeddings, vector DB, and sandboxed code execution.

Usage::

    from realai.local_runtime import LOCAL_RUNTIME

    result = LOCAL_RUNTIME.sandbox.execute("print('hello')", language="python")
    vecs = LOCAL_RUNTIME.embeddings.embed(["hello world"])
"""

from __future__ import annotations

import hashlib
import math
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CachedModel:
    """Metadata for a locally cached model.

    Attributes:
        name: Model identifier.
        path: File system path to the model.
        size_bytes: Model size in bytes.
        last_used: Unix timestamp of last access.
        backend: Backend name (e.g. "llama.cpp", "gguf").
    """
    name: str
    path: str
    size_bytes: int
    last_used: float
    backend: str


class LocalModelCache:
    """In-memory cache of locally available model metadata.

    Manages registration, lookup, and LRU eviction.
    """

    def __init__(self) -> None:
        """Initialize an empty model cache."""
        self._models: Dict[str, CachedModel] = {}

    def register(self, model: CachedModel) -> None:
        """Register a model in the cache.

        Args:
            model: CachedModel to register.
        """
        self._models[model.name] = model

    def get(self, name: str) -> Optional[CachedModel]:
        """Retrieve a cached model by name.

        Args:
            name: Model name to look up.

        Returns:
            CachedModel or None.
        """
        return self._models.get(name)

    def list_all(self) -> List[CachedModel]:
        """Return all registered cached models.

        Returns:
            List of CachedModel objects.
        """
        return list(self._models.values())

    def evict_lru(self, keep_count: int = 5) -> List[str]:
        """Remove least-recently-used models beyond keep_count.

        Args:
            keep_count: Number of models to keep.

        Returns:
            List of evicted model names.
        """
        if len(self._models) <= keep_count:
            return []
        sorted_models = sorted(
            self._models.values(),
            key=lambda m: m.last_used,
        )
        to_evict = sorted_models[:len(sorted_models) - keep_count]
        evicted = []
        for model in to_evict:
            del self._models[model.name]
            evicted.append(model.name)
        return evicted

    def total_size_bytes(self) -> int:
        """Return total size of all cached models in bytes.

        Returns:
            Sum of size_bytes across all cached models.
        """
        return sum(m.size_bytes for m in self._models.values())

    def touch(self, name: str) -> None:
        """Update last_used timestamp for a model.

        Args:
            name: Model name to touch.
        """
        model = self._models.get(name)
        if model:
            model.last_used = time.time()


class LocalEmbeddingsServer:
    """Generates text embeddings locally.

    Uses sentence_transformers if available; falls back to deterministic
    hash-based pseudo-vectors.
    """

    _VECTOR_DIM = 384

    def __init__(self) -> None:
        """Initialize the embeddings server with a null model cache."""
        self._cached_model: Optional[Any] = None

    def embed(self, texts: List[str], model: str = "default") -> List[List[float]]:
        """Generate embeddings for a list of texts.

        Args:
            texts: List of strings to embed.
            model: Model name to use (default: "default").

        Returns:
            List of float vectors, one per input text.
        """
        try:
            from sentence_transformers import SentenceTransformer
            if self._cached_model is None:
                self._cached_model = SentenceTransformer("all-MiniLM-L6-v2")
            embeddings = self._cached_model.encode(texts)
            return [list(map(float, emb)) for emb in embeddings]
        except (ImportError, Exception):
            pass
        return [self._hash_vector(text) for text in texts]

    def _hash_vector(self, text: str) -> List[float]:
        """Generate a deterministic pseudo-vector from text hash.

        Args:
            text: Input string.

        Returns:
            Normalized float vector of length _VECTOR_DIM.
        """
        digest = hashlib.sha256(text.encode()).hexdigest()
        values = []
        for i in range(0, min(len(digest), self._VECTOR_DIM * 2), 2):
            byte_val = int(digest[i:i + 2], 16)
            values.append((byte_val - 128) / 128.0)
        # Pad or truncate to _VECTOR_DIM
        while len(values) < self._VECTOR_DIM:
            seed = hashlib.md5((text + str(len(values))).encode()).hexdigest()
            for j in range(0, len(seed), 2):
                byte_val = int(seed[j:j + 2], 16)
                values.append((byte_val - 128) / 128.0)
                if len(values) >= self._VECTOR_DIM:
                    break
        vector = values[:self._VECTOR_DIM]
        # Normalize
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def is_available(self) -> bool:
        """Check if sentence_transformers is available.

        Returns:
            True if sentence_transformers can be imported.
        """
        try:
            import sentence_transformers  # noqa: F401
            return True
        except ImportError:
            return False


class LocalVectorDB:
    """Simple in-memory vector database with cosine similarity search.

    No external dependencies required.
    """

    def __init__(self) -> None:
        """Initialize an empty vector database."""
        self._vectors: Dict[str, List[float]] = {}
        self._metadata: Dict[str, Dict] = {}

    def add(
        self,
        id: str,
        vector: List[float],
        metadata: Optional[Dict] = None,
    ) -> None:
        """Add a vector with optional metadata.

        Args:
            id: Unique identifier for the vector.
            vector: Float vector to store.
            metadata: Optional metadata dict.
        """
        self._vectors[id] = vector
        self._metadata[id] = metadata or {}

    def search(
        self,
        query_vector: List[float],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find the top_k most similar vectors using cosine similarity.

        Args:
            query_vector: Query float vector.
            top_k: Number of results to return.

        Returns:
            List of dicts with id, score, and metadata, sorted by descending similarity.
        """
        if not self._vectors:
            return []

        scores = []
        q_norm = math.sqrt(sum(v * v for v in query_vector)) or 1.0

        for vid, vec in self._vectors.items():
            dot = sum(a * b for a, b in zip(query_vector, vec))
            v_norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            similarity = dot / (q_norm * v_norm)
            scores.append({
                "id": vid,
                "score": similarity,
                "metadata": self._metadata[vid],
            })

        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:top_k]

    def delete(self, id: str) -> bool:
        """Delete a vector by ID.

        Args:
            id: Vector ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        if id in self._vectors:
            del self._vectors[id]
            del self._metadata[id]
            return True
        return False

    def count(self) -> int:
        """Return the number of stored vectors.

        Returns:
            Number of vectors in the database.
        """
        return len(self._vectors)


class LocalToolSandbox:
    """Executes code in a subprocess sandbox.

    Supports Python with timeout enforcement. Other languages return
    a not-supported fallback.
    """

    def execute(
        self,
        code: str,
        language: str = "python",
        timeout: int = 10,
    ) -> Dict[str, Any]:
        """Execute code in a sandboxed subprocess.

        Args:
            code: Source code to execute.
            language: Programming language (only "python" is supported).
            timeout: Maximum execution time in seconds.

        Returns:
            Dict with status ("success"/"timeout"/"error"), output, and error.
        """
        if language.lower() not in ("python", "python3"):
            return {
                "status": "error",
                "output": "",
                "error": (
                    "Language '{0}' is not supported. "
                    "Only Python is available.".format(language)
                ),
            }

        tmp_path = None
        try:
            # Write code to temp file
            fd, tmp_path = tempfile.mkstemp(suffix=".py")
            with os.fdopen(fd, "w") as f:
                f.write(code)

            proc = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return {
                "status": "success",
                "output": proc.stdout,
                "error": proc.stderr,
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "timeout",
                "output": "",
                "error": "Execution timed out after {0} seconds.".format(timeout),
            }
        except Exception as e:
            return {
                "status": "error",
                "output": "",
                "error": str(e),
            }
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass


class _LocalRuntime:
    """Container for all local runtime components.

    Attributes:
        cache: LocalModelCache instance.
        embeddings: LocalEmbeddingsServer instance.
        vector_db: LocalVectorDB instance.
        sandbox: LocalToolSandbox instance.
    """

    def __init__(self) -> None:
        """Initialize all local runtime components."""
        self.cache = LocalModelCache()
        self.embeddings = LocalEmbeddingsServer()
        self.vector_db = LocalVectorDB()
        self.sandbox = LocalToolSandbox()


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

LOCAL_RUNTIME = _LocalRuntime()
