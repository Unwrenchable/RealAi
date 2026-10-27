"""Service-token gate for the Render / Vercel OpenAI-compatible API.

The live process is ``python -m realai.api_server`` (``realai.server.legacy_api``).
Clients and this repo already share one env var for that token: ``REALAI_API_KEY``.

``Authorization: Bearer`` is also the historical slot for an *upstream provider*
key (OpenAI, Anthropic, …). When the bearer value is one of the configured
service keys and it does not look like a cloud provider key, the handler keeps
it for the gate and does not forward it as the provider credential. Pass a
provider key as ``Authorization: Bearer`` together with ``X-API-Key`` set to
the service key when both are required on one request.

No key material is written to logs. Comparison is SHA-256 then
``hmac.compare_digest`` over every configured key.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import List, Optional, Sequence

ENV_VAR = "REALAI_API_KEY"

# Explicit local/dev names. Anything else (including the default ``production``)
# fails closed when no key is configured.
_OPEN_ENVS = frozenset({"development", "dev", "local", "test", "testing"})

_UI_GET_PATHS = frozenset({"/", "/ui", "/legacy-ui", "/fusion-ui"})


class AuthDecision(object):
    """Result of :func:`authorize`. ``body`` is an OpenAI-style error object."""

    def __init__(self, allowed, status=200, body=None):
        self.allowed = bool(allowed)
        self.status = int(status)
        self.body = body

    def __repr__(self):
        return "AuthDecision(allowed={0}, status={1})".format(self.allowed, self.status)


def parse_configured_keys(raw: Optional[str]) -> List[str]:
    """Split a comma-separated key list. Empty segments are dropped.

    Keys themselves must not contain commas. Surrounding quotes on a segment
    are removed so a dashboard value pasted with quotes still matches.
    """
    if not raw:
        return []
    keys = []
    seen = set()
    for part in str(raw).split(","):
        key = part.strip()
        if len(key) >= 2 and key[0] == key[-1] and key[0] in ("'", '"'):
            key = key[1:-1].strip()
        if not key or key in seen:
            continue
        seen.add(key)
        keys.append(key)
    return keys


def client_key() -> str:
    """First configured key for in-repo clients. Empty when unset. Never log it."""
    keys = parse_configured_keys(os.environ.get(ENV_VAR) or "")
    return keys[0] if keys else ""


def configured_keys() -> List[str]:
    """Return the live service keys.

    The process environment wins, including an explicit empty value.
    When the variable is unset, fall back to settings loaded from ``.env``
    at import (``ServerSettings`` does not export ``.env`` into ``os.environ``).
    """
    if ENV_VAR in os.environ:
        return parse_configured_keys(os.environ.get(ENV_VAR) or "")
    try:
        from realai.server.server_settings import settings
        raw = settings.REALAI_API_KEY
    except Exception:
        raw = None
    return parse_configured_keys(raw or "")


def current_env() -> str:
    """Return the live ``ENV`` value, else the settings snapshot."""
    if "ENV" in os.environ:
        return os.environ.get("ENV") or ""
    try:
        from realai.server.server_settings import settings
        return settings.ENV or ""
    except Exception:
        return ""


def _hosted() -> bool:
    from realai.cloud_fallback import is_hosted_cloud
    return bool(is_hosted_cloud())


def auth_enforced(keys: Optional[Sequence[str]] = None) -> bool:
    """True when requests must present a valid service key.

    A configured key always enforces the gate. With no key, hosted platforms
    (Render and the other markers in ``is_hosted_cloud``) and every env that
    is not an explicit local/dev name fail closed.
    """
    if keys is None:
        keys = configured_keys()
    if keys:
        return True
    if _hosted():
        return True
    return (current_env() or "").strip().lower() not in _OPEN_ENVS


def bearer_token(authorization: Optional[str]) -> str:
    """Return the credential from ``Authorization: Bearer``, or ``""``."""
    if not authorization:
        return ""
    parts = str(authorization).strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return ""
    return parts[1].strip()


def constant_time_key_match(presented: str, expected: Sequence[str]) -> bool:
    """True if ``presented`` equals any expected key.

    Both sides are hashed to a fixed length first so a length mismatch cannot
    short-circuit ``compare_digest``. Every configured key is checked.
    """
    if not presented or not expected:
        return False
    presented_digest = hashlib.sha256(presented.encode("utf-8")).digest()
    matched = False
    for candidate in expected:
        candidate_digest = hashlib.sha256(str(candidate).encode("utf-8")).digest()
        matched |= hmac.compare_digest(presented_digest, candidate_digest)
    return matched


def is_public_request(method: str, path: str) -> bool:
    """Health, CORS preflight, and the static shell are not API routes.

    ``/health`` is the only data endpoint that stays open (Render health check).
    ``OPTIONS`` must stay open or browsers cannot send ``Authorization``.
    HTML and ``/fusion-ui/*`` assets are documents, not the API. JSON routes
    such as ``/ui/providers`` and every ``/v1/*`` path are gated.
    """
    verb = (method or "GET").upper()
    raw = (path or "/").split("?", 1)[0] or "/"
    if verb == "OPTIONS":
        return True
    normalized = raw.rstrip("/") or "/"
    if normalized == "/health" and verb in ("GET", "HEAD"):
        return True
    if verb not in ("GET", "HEAD"):
        return False
    if normalized in _UI_GET_PATHS:
        return True
    if raw.startswith("/fusion-ui/"):
        return True
    return False


def openai_error(message: str, code: str = "invalid_api_key", err_type: str = "invalid_request_error"):
    """OpenAI-style error object. Never include a presented or expected key."""
    return {
        "error": {
            "message": message,
            "type": err_type,
            "param": None,
            "code": code,
        }
    }


def authorize(method: str, path: str, authorization: str = "", x_api_key: str = "") -> AuthDecision:
    """Decide whether this request may run.

    Accepts ``Authorization: Bearer <key>`` and ``X-API-Key``. Either header
    matching any configured key is enough. A wrong key is rejected even when
    the other header is absent.
    """
    if is_public_request(method, path):
        return AuthDecision(True)

    keys = configured_keys()
    if not auth_enforced(keys):
        return AuthDecision(True)

    if not keys:
        return AuthDecision(
            False,
            401,
            openai_error(
                "API authentication is not configured. Set REALAI_API_KEY on the server.",
                code="api_key_not_configured",
                err_type="server_error",
            ),
        )

    presented = []
    header_key = (x_api_key or "").strip()
    if header_key:
        presented.append(header_key)
    token = bearer_token(authorization)
    if token and token not in presented:
        presented.append(token)

    if not presented:
        return AuthDecision(
            False,
            401,
            openai_error("Missing API key. Send Authorization: Bearer <key> or X-API-Key."),
        )

    matched = False
    for item in presented:
        matched |= constant_time_key_match(item, keys)
    if not matched:
        return AuthDecision(False, 401, openai_error("Incorrect API key provided."))
    return AuthDecision(True)


def bearer_for_provider(authorization: Optional[str]) -> Optional[str]:
    """Provider API key carried in ``Authorization``, if it is not only the gate.

    A configured service key is not forwarded upstream unless it also has a
    known cloud prefix (``sk-``, ``xai-``, …), in which case the operator is
    using that same secret as the provider credential.
    """
    token = bearer_token(authorization)
    if not token:
        return None
    keys = configured_keys()
    if keys and constant_time_key_match(token, keys):
        from realai.cloud_fallback import detect_cloud_provider_from_key
        if not detect_cloud_provider_from_key(token):
            return None
    return token


def auth_startup_message() -> str:
    """One-line boot log. Counts keys; never prints key material."""
    keys = configured_keys()
    if keys:
        noun = "key" if len(keys) == 1 else "keys"
        return (
            "API auth: REALAI_API_KEY is set ({0} {1}). "
            "Every API route except GET /health requires "
            "Authorization: Bearer <key> or X-API-Key."
        ).format(len(keys), noun)
    if auth_enforced(keys):
        return (
            "API auth: REALAI_API_KEY is not set. Refusing API requests (fail closed). "
            "Set REALAI_API_KEY on the host. Comma-separate multiple keys. "
            "GET /health stays open."
        )
    return (
        "API auth: REALAI_API_KEY is not set and ENV={0} is a local/dev environment. "
        "API routes are open. Set REALAI_API_KEY before exposing this process."
    ).format(current_env() or "development")
