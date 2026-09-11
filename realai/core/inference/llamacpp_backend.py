"""Llama.cpp backend integration for local inference.

This module provides integration with llama.cpp for local model inference.
For the complete implementation, see realai/server/llama_cli_backend.py
which implements a production-ready backend that calls llama-cli.exe.

Quick Start:
    1. Download llama-cli.exe from https://github.com/ggerganov/llama.cpp
    2. Download GGUF models from Hugging Face
    3. Configure models in realai/models/registry.json
    4. Start server: python -m realai.server.app

See docs/local-llama-setup.md for complete documentation.
"""

from pathlib import Path


def is_available():
    """Check if llama.cpp backend is available."""
    try:
        from realai.server.llama_cli_backend import LlamaCliBackend
        backend = LlamaCliBackend()
        return backend.available()
    except ImportError:
        return False


def get_backend():
    """Get the llama-cli backend instance."""
    from realai.server.llama_cli_backend import LlamaCliBackend
    return LlamaCliBackend()


# For backwards compatibility
class LlamaCppBackend:
    """Stub class pointing to the real implementation."""

    def __init__(self):
        try:
            from realai.server.llama_cli_backend import LlamaCliBackend
            self._backend = LlamaCliBackend()
        except ImportError:
            self._backend = None

    def available(self):
        return self._backend is not None and self._backend.available()

    def generate(self, model_path, prompt, sampling_config):
        if not self._backend:
            raise RuntimeError("llama-cli backend not available")
        return self._backend.generate(model_path, prompt, sampling_config)
