"""RealAI model providers.

Exports provider_registry for abilities that call load_default_model().
Submodules (local_llama, voice, etc.) stay importable as realai.providers.<name>.
"""

from .provider_registry import LocalCompletionModel, ProviderRegistry, provider_registry

__all__ = [
    "LocalCompletionModel",
    "ProviderRegistry",
    "provider_registry",
]

# Voice provider is lazy — import realai.providers.voice when needed.
