"""Embedding backend abstraction for structured server."""

import hashlib
import math
from typing import Dict, List

from .logging_utils import setup_logging

logger = setup_logging()


class EmbeddingBackend(object):
    """Embedding backend interface."""

    name = 'base'

    def embed(self, model_path: str, texts: List[str]):
        raise NotImplementedError


class SentenceTransformerBackend(EmbeddingBackend):
    """Local sentence-transformers backend."""

    name = 'sentence-transformers'

    def __init__(self):
        self._models: Dict[str, object] = {}

    def embed(self, model_path: str, texts: List[str]):
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as exc:
            logger.warning('SentenceTransformer unavailable for %s: %s', model_path, exc)
            return None
        if model_path not in self._models:
            self._models[model_path] = SentenceTransformer(model_path)
        vectors = self._models[model_path].encode(texts, convert_to_numpy=True)
        return vectors.tolist()


class DeterministicEmbeddingBackend(EmbeddingBackend):
    """Dependency-free embedding backend used for local fallback and tests."""

    name = 'deterministic'
    dimensions = 64

    def embed(self, model_path: str, texts: List[str]):
        vectors = []
        for text in texts:
            seed = hashlib.sha256('{0}:{1}'.format(model_path, text).encode('utf-8')).digest()
            values = []
            current = seed
            while len(values) < self.dimensions:
                for index in range(0, len(current), 4):
                    chunk = current[index:index + 4]
                    if len(chunk) < 4:
                        continue
                    raw = int.from_bytes(chunk, 'big')
                    values.append((raw / 4294967295.0) * 2.0 - 1.0)
                    if len(values) >= self.dimensions:
                        break
                current = hashlib.sha256(current).digest()
            norm = math.sqrt(sum(value * value for value in values)) or 1.0
            vectors.append([round(value / norm, 8) for value in values[:self.dimensions]])
        return vectors


class RealAIFallbackEmbeddingBackend(EmbeddingBackend):
    """Legacy fallback embedding backend."""

    name = 'realai-fallback'

    def embed(self, model_path: str, texts: List[str]):
        try:
            from .. import RealAI

            model = RealAI(model_name=model_path, provider='local', use_local=True)
            response = model.create_embeddings(input_text=texts, model=model_path)
            return [item.get('embedding', []) for item in response.get('data', [])]
        except Exception as exc:
            logger.warning('RealAI embedding fallback unavailable for %s: %s', model_path, exc)
            return None


class EmbeddingResolver(object):
    """Backend resolver for embeddings."""

    def __init__(self):
        self._local = SentenceTransformerBackend()
        self._deterministic = DeterministicEmbeddingBackend()
        self._fallback = RealAIFallbackEmbeddingBackend()

    def embed(self, backend_hint: str, model_path: str, texts: List[str]):
        hint = (backend_hint or '').lower()
        if hint in ('hf', 'sentence-transformers', 'local'):
            vectors = self._local.embed(model_path, texts)
            if vectors is not None:
                return vectors, self._local.name
        if hint in ('deterministic', 'stub', 'realai-fallback', ''):
            vectors = self._deterministic.embed(model_path, texts)
            if vectors is not None:
                return vectors, self._deterministic.name
        vectors = self._fallback.embed(model_path, texts)
        if vectors is not None:
            return vectors, self._fallback.name
        return self._deterministic.embed(model_path, texts), self._deterministic.name


EMBEDDING_RESOLVER = EmbeddingResolver()
