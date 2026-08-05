"""Structured server entrypoints for RealAI."""

from .app import app, main
from .config import get_model_config, list_models, load_registry, load_settings
from .router import dispatch_request, handle_chat_request, handle_embeddings_request

__all__ = [
    "app",
    "main",
    "dispatch_request",
    "get_model_config",
    "load_settings",
    "handle_chat_request",
    "handle_embeddings_request",
    "list_models",
    "load_registry",
]
