"""AMD-optimized inference settings for RealAI.

Vulkan llama.cpp on :8080. No CUDA. Import is data only.
"""

from __future__ import annotations

import os
from typing import Any, Dict

AMD_INFERENCE: Dict[str, Any] = {
    "backend": "vulkan-llama",
    "device": "amd",
    "gpu_api": "vulkan",
    "cuda": False,
    "rocm": False,
    "host": "127.0.0.1",
    "port": 8080,
    "default_chat_model": "realai-1.0",
    "default_embed_model": "realai-embed",
    "n_gpu_layers": -1,
    "n_ctx": 8192,
    "n_batch": 512,
    "n_threads": 0,
    "n_predict": 512,
    "temperature": 0.7,
    "top_p": 0.9,
    "flash_attn": False,
    "mlock": False,
    "mmap": True,
    "offload_kqv": True,
}

ENV_BASE_KEYS = ("REALAI_VULKAN_BASE", "LOCAL_LLAMA_URL")


def vulkan_base_url() -> str:
    for key in ENV_BASE_KEYS:
        value = os.environ.get(key)
        if value:
            return value.rstrip("/")
    host = AMD_INFERENCE["host"]
    port = AMD_INFERENCE["port"]
    return "http://{0}:{1}".format(host, port)


def llama_server_args(model_path: str) -> list:
    """Static argv for an AMD Vulkan llama-server. Not executed here."""
    cfg = AMD_INFERENCE
    return [
        "--model",
        model_path,
        "--host",
        str(cfg["host"]),
        "--port",
        str(cfg["port"]),
        "--n-gpu-layers",
        str(cfg["n_gpu_layers"]),
        "--ctx-size",
        str(cfg["n_ctx"]),
        "--batch-size",
        str(cfg["n_batch"]),
        "--n-predict",
        str(cfg["n_predict"]),
    ]
