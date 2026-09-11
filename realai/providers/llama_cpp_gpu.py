"""GPU llama.cpp provider (reconstructed dest-empty stub).

Original gold body was never recovered. Every copy of this filename in
quarantine, parked unify trees, and archives is 0 bytes (empty SHA-1
da39a3ee). Live GPU chat is realai.providers.local_llama against Vulkan
llama-server on :8080 (REALAI_VULKAN_BASE / LOCAL_LLAMA_URL). Craft
starts that server via ensure_gpu_server.

This module is a named alias so ``realai.providers.llama_cpp_gpu``
imports resolve. Not recovered gold. Park and replace if a size>0
original appears.
"""

from __future__ import annotations

from realai.providers.local_llama import (
    BASE_URL,
    local_llama_chat,
    local_llama_completion,
    local_llama_health,
)

# Historical names some callers used for the GPU-bound llama.cpp client.
llama_cpp_gpu_health = local_llama_health
llama_cpp_gpu_completion = local_llama_completion
llama_cpp_gpu_chat = local_llama_chat

__all__ = [
    "BASE_URL",
    "llama_cpp_gpu_health",
    "llama_cpp_gpu_completion",
    "llama_cpp_gpu_chat",
    "local_llama_health",
    "local_llama_completion",
    "local_llama_chat",
]