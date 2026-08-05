"""RealAI provider adapters (local-first)."""

from .local_llama import local_llama_chat, local_llama_completion, local_llama_health

__all__ = [
    "local_llama_chat",
    "local_llama_completion",
    "local_llama_health",
]
