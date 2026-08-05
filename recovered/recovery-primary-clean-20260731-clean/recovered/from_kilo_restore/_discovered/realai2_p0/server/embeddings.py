"""Embedding helpers for the structured RealAI server."""

from .config import get_model_config
from .embeddings_backend import EMBEDDING_RESOLVER
from .metrics import REQUESTS

def embed(model_name, texts):
    """Encode texts into embedding vectors."""
    cfg = get_model_config(model_name)
    if cfg['type'] != 'embedding':
        raise ValueError('Model {0} is not embedding type'.format(model_name))
    REQUESTS.labels(endpoint='embeddings', model=model_name).inc()

    vectors, _backend_name = EMBEDDING_RESOLVER.embed(
        cfg.get('backend', ''),
        cfg.get('path', model_name),
        texts,
    )
    return vectors
