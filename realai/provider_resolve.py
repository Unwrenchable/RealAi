"""Resolve the provider for a stdlib API-server request.

Self-hosted RealAI keys often have no cloud prefix (``sk-``, ``xai-``, …).
When ``Authorization: Bearer`` is present and ``X-Provider`` is omitted,
prefix detection is tried first; on miss we default to ``realai`` (override
with ``REALAI_PROVIDER``) instead of raising.

Explicit ``X-Provider`` (openai, anthropic, grok, …) always wins. Known
cloud key prefixes are left unset so RealAI's existing auto-detect /
local-only policy is unchanged — this does **not** force cloud keys
through the self-host provider.
"""

from __future__ import annotations

import os
from typing import Mapping, Optional


def default_selfhost_provider() -> str:
    """Return the self-host provider id (env ``REALAI_PROVIDER``, default ``realai``)."""
    value = (os.environ.get("REALAI_PROVIDER") or "realai").strip()
    return value or "realai"


def detect_provider_from_key(
    api_key: Optional[str],
    prefixes: Mapping[str, str],
) -> Optional[str]:
    """Return the provider implied by a known API-key prefix, else ``None``."""
    if not api_key:
        return None
    for prefix, name in prefixes.items():
        if api_key.startswith(prefix):
            return name
    return None


def resolve_request_provider(
    x_provider: Optional[str],
    api_key: Optional[str],
    prefixes: Mapping[str, str],
) -> Optional[str]:
    """Pick the ``provider`` argument for :class:`~realai.RealAI`.

    * Explicit ``X-Provider`` (anything other than empty / ``auto``) wins.
    * Known key prefixes return ``None`` so RealAI auto-detects as before.
    * Bearer present, no usable header, prefix miss → :func:`default_selfhost_provider`.
    * No Bearer key → ``None`` (caller may fall back to env keys).
    """
    explicit = (x_provider or "").strip()
    if explicit and explicit.lower() not in ("auto", "default"):
        return explicit
    if not api_key:
        return None
    if detect_provider_from_key(api_key, prefixes):
        return None
    return default_selfhost_provider()
