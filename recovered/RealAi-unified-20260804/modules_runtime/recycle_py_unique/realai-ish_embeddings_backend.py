"""Embedding backend abstraction for structured server."""

from typing import Dict, List

from realai import RealAI

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


class RealAIFallbackEmbeddingBackend(EmbeddingBackend):
    """Legacy fallback embedding backend."""

    name = 'realai-fallback'

    def embed(self, model_path: str, texts: List[str]):
        model = RealAI(model_name=model_path, provider='local', use_local=True)
        response = model.create_embeddings(input_text=texts, model=model_path)
        return [item.get('embedding', []) for item in response.get('data', [])]


class EmbeddingResolver(object):
    """Backend resolver for embeddings."""

    def __init__(self):
        self._local = SentenceTransformerBackend()
        self._fallback = RealAIFallbackEmbeddingBackend()

    def embed(self, backend_hint: str, model_path: str, texts: List[str]):
        if (backend_hint or '').lower() in ('hf', 'sentence-transformers', 'local'):
            vectors = self._local.embed(model_path, texts)
            if vectors is not None:
                return vectors, self._local.name
        vectors = self._fallback.embed(model_path, texts)
        return vectors, self._fallback.name


EMBEDDING_RESOLVER = EmbeddingResolver()

