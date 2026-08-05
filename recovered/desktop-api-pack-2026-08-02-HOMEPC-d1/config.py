import os
from typing import List, Set

DEFAULT_API_KEYS: Set[str] = {"realai-dev", "realai-demo"}
DEFAULT_MODEL_ID = "realai-echo-1"
DEFAULT_MODEL_OWNER = "realai"
DEFAULT_MODEL_DESCRIPTION = "Echo-style mock model for RealAI bootstrap"


def get_valid_api_keys() -> Set[str]:
    """Return the list of accepted API keys.

    Keys can be supplied via REALAI_API_KEYS (comma-separated). Falls back to
    a small built-in set for local usage and quick starts.
    """
    env_keys = os.getenv("REALAI_API_KEYS")
    if env_keys:
        return {key.strip() for key in env_keys.split(",") if key.strip()}
    return set(DEFAULT_API_KEYS)


def get_default_models(now: int) -> List[dict]:
    """Describe the default models exposed by the router."""
    return [
        {
            "id": DEFAULT_MODEL_ID,
            "object": "model",
            "created": now,
            "owned_by": DEFAULT_MODEL_OWNER,
            "description": DEFAULT_MODEL_DESCRIPTION,
        }
    ]
