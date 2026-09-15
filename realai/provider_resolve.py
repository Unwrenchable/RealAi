"""Resolve the provider for a stdlib API-server request.

Self-hosted RealAI keys often have no cloud prefix (``sk-``, ``xai-``, …).
When ``Authorization: Bearer`` is present and ``X-Provider`` is omitted or
``auto``, prefix detection is tried first; on miss we default to ``realai``
(override with ``REALAI_PROVIDER``) instead of raising.

``local`` and ``realai`` are the same self-host path. Clients should send
``X-Provider: realai`` for both dropdown values so Nest / RackUp contracts
agree. Explicit cloud providers (openai, anthropic, grok, …) always win.
Known cloud key prefixes are left unset so RealAI's existing auto-detect /
local-only policy is unchanged — this does **not** force cloud keys through
the self-host provider.
"""

from __future__ import annotations

import os
from typing import Mapping, Optional

#: Wire + UI aliases for the self-host provider. Both map to ``realai``.
SELFHOST_ALIASES = frozenset({"local", "realai"})


def default_selfhost_provider() -> str:
    """Return the self-host provider id (env ``REALAI_PROVIDER``, default ``realai``)."""
    value = (os.environ.get("REALAI_PROVIDER") or "realai").strip()
    return value or "realai"


def is_selfhost_alias(name: Optional[str]) -> bool:
    """True if *name* is ``local`` or ``realai`` (case-insensitive)."""
    return (name or "").strip().lower() in SELFHOST_ALIASES


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
    """Pick the wire provider id for a request.

    * Explicit ``X-Provider`` other than empty / ``auto`` wins.
    * ``local`` and ``realai`` both become :func:`default_selfhost_provider`.
    * Known key prefixes return ``None`` so RealAI auto-detects as before.
    * Bearer present, ``auto`` / missing header, prefix miss → self-host default.
    * No Bearer key → ``None`` (caller may fall back to env keys).
    """
    explicit = (x_provider or "").strip()
    if explicit and explicit.lower() not in ("auto", "default"):
        if is_selfhost_alias(explicit):
            return default_selfhost_provider()
        return explicit
    if not api_key:
        return None
    if detect_provider_from_key(api_key, prefixes):
        return None
    return default_selfhost_provider()


def realai_constructor_provider(resolved: Optional[str]) -> Optional[str]:
    """Map a resolved wire provider to the :class:`~realai.RealAI` constructor.

    Self-host aliases (``local`` / ``realai`` / ``REALAI_PROVIDER``) use the
    existing ``provider="local"`` local-model path.
    """
    if not resolved:
        return None
    name = resolved.strip()
    if is_selfhost_alias(name) or name.lower() == default_selfhost_provider().lower():
        return "local"
    return name
