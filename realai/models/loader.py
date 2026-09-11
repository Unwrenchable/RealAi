"""Local model loader for RealAI.

Prefers the AMD Vulkan llama-server on :8080, then local_models,
then a dry registry lookup. Import does not load weights.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from realai.config.amd_inference import AMD_INFERENCE, vulkan_base_url


def _package_root() -> Path:
    return Path(__file__).resolve().parents[1]


class ModelLoader:
    def __init__(self, settings: Optional[Dict[str, Any]] = None) -> None:
        self.settings = dict(settings or AMD_INFERENCE)
        self.base_url = vulkan_base_url()
        self._loaded: Dict[str, Any] = {}

    def describe(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        mid = model_id or self.settings.get("default_chat_model") or "realai-1.0"
        models_dir = _package_root() / "models"
        local_dir = models_dir / mid
        return {
            "id": mid,
            "backend": self.settings.get("backend", "vulkan-llama"),
            "base_url": self.base_url,
            "n_gpu_layers": self.settings.get("n_gpu_layers", -1),
            "ctx": self.settings.get("n_ctx", 8192),
            "path": str(local_dir) if local_dir.exists() else None,
            "gpu": "amd-vulkan",
        }

    def health(self) -> Dict[str, Any]:
        try:
            from realai.providers.local_llama import local_llama_health

            return local_llama_health()
        except Exception as exc:
            return {"ok": False, "base": self.base_url, "error": str(exc)}

    def load(self, model_id: Optional[str] = None) -> Dict[str, Any]:
        """Resolve a model. Does not spawn llama-server or import CUDA."""
        info = self.describe(model_id)
        self._loaded[info["id"]] = info
        return info

    def chat(self, messages, max_tokens: Optional[int] = None, temperature: Optional[float] = None):
        from realai.providers.local_llama import local_llama_chat

        return local_llama_chat(
            messages=list(messages),
            max_tokens=int(max_tokens or self.settings.get("n_predict", 512)),
            temperature=float(temperature or self.settings.get("temperature", 0.7)),
            model=os.environ.get("REALAI_BACKEND_MODEL") or self.settings.get("default_chat_model"),
        )


def get_model_loader() -> ModelLoader:
    return ModelLoader()
