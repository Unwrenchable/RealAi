"""Provider config authority for RealAI (gold).

Single definition of PROVIDER_CONFIGS, PROVIDER_ENV_VARS, key-prefix detection
and _detect_provider. Local-first: with REALAI_BOT_LOCAL_ONLY on (default) the
provider resolves to ``local`` (Vulkan llama-server) and no cloud key is needed.
Cloud entries are optional twins. Import from here; ``realai._v1_client``,
``realai`` and ``realai.sdk`` only re-export.
"""
from __future__ import annotations

import os
from typing import Dict, Optional

#: Name of the local-first provider (Vulkan llama-server, loopback only).
LOCAL_PROVIDER = "local"

# ---------------------------------------------------------------------------
# Provider configuration for real AI API routing
# ---------------------------------------------------------------------------

#: Configuration for supported external AI providers.
PROVIDER_CONFIGS: Dict[str, Dict[str, str]] = {
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "api_format": "openai",
    },
    "anthropic": {
        "base_url": "https://api.anthropic.com",
        "default_model": "claude-3-5-haiku-20241022",
        "api_format": "anthropic",
    },
    "grok": {
        "base_url": "https://api.x.ai/v1",
        "default_model": "grok-beta",
        "api_format": "openai",
    },
    "gemini": {
        # Google exposes an OpenAI-compatible endpoint for Gemini models.
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-1.5-flash",
        "api_format": "openai",
    },
    "openrouter": {
        # OpenRouter aggregates hundreds of models via a single OpenAI-compatible API.
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "openai/gpt-4o-mini",
        "api_format": "openai",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "default_model": "mistral-small-latest",
        "api_format": "openai",
    },
    "together": {
        "base_url": "https://api.together.xyz/v1",
        "default_model": "meta-llama/Llama-3-8b-chat-hf",
        "api_format": "openai",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "default_model": "deepseek-chat",
        "api_format": "openai",
    },
    "perplexity": {
        "base_url": "https://api.perplexity.ai",
        "default_model": "llama-3.1-sonar-small-128k-online",
        "api_format": "openai",
    },
}

#: Maps API key prefixes to provider names for auto-detection.
_KEY_PREFIX_TO_PROVIDER: Dict[str, str] = {
    "sk-ant-": "anthropic",
    "sk-or-v1-": "openrouter",
    "sk-proj-": "openai",
    "sk-": "openai",
    "xai-": "grok",
    "AIza": "gemini",
    "pplx-": "perplexity",
}

#: Maps provider names to the environment variable used to pass their API key
#: via the process environment (e.g. set by the GUI launcher).
#: The insertion order defines the fallback priority used by the API server.
PROVIDER_ENV_VARS: Dict[str, str] = {
    "openai": "REALAI_OPENAI_API_KEY",
    "anthropic": "REALAI_ANTHROPIC_API_KEY",
    "grok": "REALAI_GROK_API_KEY",
    "gemini": "REALAI_GEMINI_API_KEY",
    "openrouter": "REALAI_OPENROUTER_API_KEY",
    "mistral": "REALAI_MISTRAL_API_KEY",
    "together": "REALAI_TOGETHER_API_KEY",
    "deepseek": "REALAI_DEEPSEEK_API_KEY",
    "perplexity": "REALAI_PERPLEXITY_API_KEY",
}


def _detect_provider(api_key: Optional[str], provider: Optional[str]) -> Optional[str]:
    """Detect the AI provider from an explicit name or API key prefix.

    Args:
        api_key: The raw API key string (may be ``None``).
        provider: An explicit provider name that overrides key-based detection.

    Returns:
        The lower-cased provider name, or ``None`` if it cannot be determined.
        When ``REALAI_BOT_LOCAL_ONLY`` is on (default), chat detection is forced
        to ``local`` and cloud key prefixes are ignored.
    """
    local_only = os.environ.get("REALAI_BOT_LOCAL_ONLY", "1").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
        "",
    )
    if local_only and (provider is None or str(provider).lower() in ("", "auto", "default")):
        return "local"
    if provider:
        return provider.lower()
    if local_only:
        return "local"
    if api_key:
        for prefix, name in _KEY_PREFIX_TO_PROVIDER.items():
            if api_key.startswith(prefix):
                return name
    return None


__all__ = ["LOCAL_PROVIDER", "PROVIDER_CONFIGS", "PROVIDER_ENV_VARS", "_KEY_PREFIX_TO_PROVIDER", "_detect_provider"]
