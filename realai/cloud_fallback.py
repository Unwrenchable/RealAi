"""Cloud vs local generation routing for self-host ``realai`` / ``local``.

Render's ``python -m realai.api_server`` never reads Travis's PC file
``C:\\models\\checkpoints_lora\\registry.json``. The registry RealAI actually
loads for ``default_llm`` is ``~/.realai/local_models.json`` (see
``realai.core.local_models.LocalModelManager``). Repo
``realai/config/models.json`` is a local Hive catalog only.

When the Cloud UI sends ``X-Provider: realai`` and no GGUF is loaded on this
host, prefer a configured cloud provider key instead of the generic
"register default_llm" placeholder.
"""

from __future__ import annotations

import os
from typing import Any, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlparse

# Mirrors ``realai.PROVIDER_ENV_VARS`` plus public names used on Render / Vercel.
CLOUD_KEY_ENVS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("openai", ("REALAI_OPENAI_API_KEY", "OPENAI_API_KEY")),
    ("anthropic", ("REALAI_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY")),
    ("grok", ("REALAI_GROK_API_KEY", "XAI_API_KEY")),
    ("gemini", ("REALAI_GEMINI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY")),
    ("openrouter", ("REALAI_OPENROUTER_API_KEY", "OPENROUTER_API_KEY")),
    ("mistral", ("REALAI_MISTRAL_API_KEY", "MISTRAL_API_KEY")),
    ("together", ("REALAI_TOGETHER_API_KEY", "TOGETHER_API_KEY")),
    ("deepseek", ("REALAI_DEEPSEEK_API_KEY", "DEEPSEEK_API_KEY")),
    ("perplexity", ("REALAI_PERPLEXITY_API_KEY", "PERPLEXITY_API_KEY")),
)

_KEY_PREFIXES: Tuple[Tuple[str, str], ...] = (
    ("sk-ant-", "anthropic"),
    ("sk-or-v1-", "openrouter"),
    ("sk-proj-", "openai"),
    ("sk-", "openai"),
    ("xai-", "grok"),
    ("AIza", "gemini"),
    ("pplx-", "perplexity"),
)

_FALSE = frozenset({"0", "false", "off", "no"})
_TRUE = frozenset({"1", "true", "yes", "on", "auto"})
_HOSTED_ENV_MARKERS = (
    "RENDER",
    "RENDER_SERVICE_ID",
    "RENDER_INSTANCE_ID",
    "FLY_APP_NAME",
    "RAILWAY_ENVIRONMENT",
    "RAILWAY_ENVIRONMENT_ID",
    "K_SERVICE",
    "AWS_LAMBDA_FUNCTION_NAME",
)

GENERIC_DEFAULT_LLM_PLACEHOLDER = (
    "Local RealAI is selected, but no local model is configured/loaded yet. "
    "Register a local model and set it as default_llm, then retry."
)


def is_hosted_cloud() -> bool:
    """True on Render / Fly / Railway / similar — not a GPU Hive PC."""
    for name in _HOSTED_ENV_MARKERS:
        if (os.environ.get(name) or "").strip():
            return True
    return False


def local_console_url() -> str:
    return (
        (os.environ.get("NEXT_PUBLIC_LOCAL_CONSOLE_URL") or "").strip()
        or "http://127.0.0.1:8001/console"
    )


def vulkan_base() -> str:
    return (os.environ.get("REALAI_VULKAN_BASE") or "http://127.0.0.1:8080").rstrip("/")


def _host_is_loopback(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in {"127.0.0.1", "localhost", "::1"}


def vulkan_forward_enabled() -> bool:
    """Proxy chat to local llama-server only on loopback Hive — never on Render.

    Hosted cloud (Render / Fly / Railway / …) is an unconditional deny, including
    ``REALAI_VULKAN_FORWARD=force``. A non-loopback ``REALAI_VULKAN_BASE`` is
    always rejected.
    """
    if is_hosted_cloud():
        return False
    flag = (os.environ.get("REALAI_VULKAN_FORWARD") or "auto").strip().lower()
    if flag in _FALSE:
        return False
    if not _host_is_loopback(vulkan_base()):
        return False
    return True


def looks_like_local_model_id(model_name: Optional[str]) -> bool:
    """True for Hive / self-host ids that OpenAI etc. will not recognize.

    Does not treat every ``qwen*`` / ``llama*`` string as local — those are
    valid cloud model ids (Together, Groq, …).
    """
    name = (model_name or "").strip().lower()
    if not name:
        return True
    if name.endswith(".gguf"):
        return True
    if name.startswith("realai"):
        return True
    if name in {"local", "default", "auto", "qwen-coder-7b", "llama-local"}:
        return True
    return False


def detect_cloud_provider_from_key(api_key: Optional[str]) -> Optional[str]:
    if not api_key:
        return None
    for prefix, name in _KEY_PREFIXES:
        if api_key.startswith(prefix):
            return name
    return None


def _env_key(names: Sequence[str]) -> str:
    for name in names:
        value = (os.environ.get(name) or "").strip()
        if value:
            return value
    return ""


def iter_configured_cloud_credentials() -> Tuple[Tuple[str, str], ...]:
    """Return ``(provider, api_key)`` pairs from process env (first key wins per provider)."""
    found = []
    for provider, env_names in CLOUD_KEY_ENVS:
        key = _env_key(env_names)
        if key:
            found.append((provider, key))
    return tuple(found)


def first_configured_cloud_credentials() -> Optional[Tuple[str, str]]:
    rows = iter_configured_cloud_credentials()
    return rows[0] if rows else None


def credentials_for_provider(provider: Optional[str]) -> str:
    """Return the env API key for one named cloud provider, or ``""``."""
    wanted = (provider or "").strip().lower()
    if not wanted:
        return ""
    for name, env_names in CLOUD_KEY_ENVS:
        if name == wanted:
            return _env_key(env_names)
    return ""


def env_credentials_for_request(provider: Optional[str]) -> Optional[Tuple[str, str]]:
    """Pick env credentials for ``_get_model``.

    Explicit cloud ``X-Provider`` gets **that** provider's key only (never an
    OpenAI key stuffed into Anthropic). Self-host / missing provider uses the
    first configured cloud key for fallback.
    """
    from .provider_resolve import default_selfhost_provider, is_selfhost_alias

    name = (provider or "").strip().lower()
    selfhost = (
        (not name)
        or is_selfhost_alias(name)
        or name == default_selfhost_provider().lower()
    )
    if not selfhost:
        key = credentials_for_provider(name)
        return (name, key) if key else None
    return first_configured_cloud_credentials()


def cloud_fallback_disabled() -> bool:
    flag = (os.environ.get("REALAI_CLOUD_FALLBACK") or "").strip().lower()
    return flag in _FALSE


def discover_cloud_fallback(
    request_api_key: Optional[str] = None,
) -> Optional[Tuple[str, str]]:
    """Pick a cloud ``(provider, api_key)`` when local GGUF is unavailable.

    Order:
    1. ``REALAI_CLOUD_FALLBACK=off`` → no fallback
    2. ``REALAI_CLOUD_FALLBACK=<provider>`` → that provider's env key
    3. Request Bearer if it has a known cloud prefix
    4. First configured ``OPENAI_API_KEY`` / ``REALAI_*_API_KEY``
    """
    if cloud_fallback_disabled():
        return None

    explicit = (os.environ.get("REALAI_CLOUD_FALLBACK") or "").strip()
    if explicit and explicit.lower() not in _TRUE:
        wanted = explicit.lower()
        for provider, env_names in CLOUD_KEY_ENVS:
            if provider == wanted:
                key = _env_key(env_names)
                return (provider, key) if key else None
        return None

    prefixed = detect_cloud_provider_from_key(request_api_key)
    if prefixed and request_api_key:
        return (prefixed, request_api_key)

    return first_configured_cloud_credentials()


def local_default_llm_ready(manager: Any = None) -> bool:
    """True when ``default_llm`` is set *and* its GGUF path exists.

    Uses ``LocalModelManager`` → ``~/.realai/local_models.json``. Does not
    read ``C:\\models\\checkpoints_lora\\registry.json``.
    """
    if manager is None:
        return False
    try:
        name = manager.config.get("default_llm") if getattr(manager, "config", None) else None
    except Exception:
        return False
    if not name:
        return False
    try:
        return bool(manager.is_model_available(name))
    except Exception:
        return False


def missing_generation_message(*, use_local: bool = True) -> str:
    """Human-readable reason chat cannot generate — cloud vs Hive, not a PC registry miss."""
    console = local_console_url()
    if not use_local:
        return (
            "No API key configured. Select Local RealAI to run locally without a key, "
            "or paste a provider API key in the settings bar."
        )
    if is_hosted_cloud():
        return (
            "This Cloud API has no local GPU model (no GGUF / Vulkan on Render). "
            f"Open Local Hive on your PC ({console}) or set a cloud provider key "
            "(OPENAI_API_KEY, REALAI_OPENAI_API_KEY, or REALAI_CLOUD_FALLBACK). "
            "default_llm is not missing from a PC registry on this host — "
            "it lives in ~/.realai/local_models.json on the machine that loads GGUF."
        )
    return (
        "Local RealAI has no GGUF loaded on this machine. "
        "Set default_llm in ~/.realai/local_models.json (the file RealAI actually loads — "
        "not C:\\models\\checkpoints_lora\\registry.json and not repo realai/config/models.json), "
        f"start Local Hive ({console}), or set OPENAI_API_KEY / REALAI_*_API_KEY to use cloud fallback."
    )


def provider_can_call_cloud(
    provider: Optional[str],
    api_key: Optional[str],
    base_url: Optional[str],
    provider_configs: Mapping[str, Mapping[str, str]],
) -> bool:
    if not provider or not api_key:
        return False
    name = provider.strip().lower()
    if name in {"local", "realai"}:
        return False
    if name in provider_configs:
        return bool(base_url or provider_configs.get(name, {}).get("base_url"))
    # Custom REALAI_PROVIDER / X-Base-URL self-host endpoints.
    return bool(base_url)


def bind_cloud_provider(
    instance: Any,
    provider: str,
    api_key: str,
    provider_configs: Mapping[str, Mapping[str, str]],
) -> None:
    """Attach cloud credentials + default model id onto a RealAI instance."""
    cfg = dict(provider_configs.get(provider) or {})
    instance.provider = provider
    instance.api_key = api_key
    override = getattr(instance, "_base_url_override", None)
    instance.base_url = override or cfg.get("base_url") or getattr(instance, "base_url", "") or ""
    instance._api_format = cfg.get("api_format", "openai")
    requested = getattr(instance, "model_name", None)
    if looks_like_local_model_id(requested) or requested == "realai-2.0":
        instance._provider_model = cfg.get("default_model") or requested
    else:
        instance._provider_model = requested
    instance._cloud_fallback_applied = True


def apply_cloud_fallback_to_instance(
    instance: Any,
    provider_configs: Mapping[str, Mapping[str, str]],
    *,
    local_ready: Optional[bool] = None,
) -> bool:
    """If local GGUF is unusable, bind env/request cloud credentials.

    Returns True when cloud fallback was applied (or already bound).
    """
    if cloud_fallback_disabled():
        return False
    if provider_can_call_cloud(
        getattr(instance, "provider", None),
        getattr(instance, "api_key", None),
        getattr(instance, "base_url", None),
        provider_configs,
    ):
        return True
    if local_ready is None:
        local_ready = local_default_llm_ready(getattr(instance, "_model_manager", None))
    if local_ready:
        return False
    found = discover_cloud_fallback(getattr(instance, "api_key", None))
    if not found:
        return False
    bind_cloud_provider(instance, found[0], found[1], provider_configs)
    return True
