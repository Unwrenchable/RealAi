"""Inference backend abstractions and registries."""

from .local_stub import LocalStubChat, LocalStubEmbeddings
from .registry import InferenceRegistry

__all__ = ["InferenceRegistry", "LocalStubChat", "LocalStubEmbeddings"]

