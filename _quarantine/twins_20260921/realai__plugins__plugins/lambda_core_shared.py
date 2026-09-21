"""
Shared core module for Lambda functions.

This module contains common provider routing logic, configurations,
and utilities used across all Lambda functions.
"""

import json
import os
from typing import Dict, Any, Optional

# Re-export provider configurations from realai module
from realai import (
    PROVIDER_CONFIGS,
    PROVIDER_ENV_VARS,
    _KEY_PREFIX_TO_PROVIDER,
    _detect_provider,
    RealAI
)


def get_model_from_event(event: Dict[str, Any]) -> RealAI:
    """
    Build a RealAI instance from Lambda event.

    Reads the API key from the Authorization header, the optional provider
    override from X-Provider, and the optional base URL from X-Base-URL.
    Falls back to environment variables if no Authorization header is present.

    Args:
        event: Lambda event dict containing headers and body

    Returns:
        RealAI instance configured for the request
    """
    headers = event.get("headers", {})
    body = {}

    if event.get("body"):
        try:
            body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
        except json.JSONDecodeError:
            body = {}

    # Extract model name from body
    model_name = body.get("model", "realai-2.0")

    # Extract API key from Authorization header
    auth = headers.get("authorization", headers.get("Authorization", ""))
    api_key = auth[len("Bearer "):].strip() if auth.startswith("Bearer ") else None

    # Extract optional overrides
    provider = headers.get("x-provider", headers.get("X-Provider")) or None
    base_url = headers.get("x-base-url", headers.get("X-Base-URL")) or None

    # Fall back to environment variables
    if not api_key:
        for _provider, _env_var in PROVIDER_ENV_VARS.items():
            _key = os.environ.get(_env_var, "")
            if _key:
                api_key = _key
                if not provider:
                    provider = _provider
                break

    return RealAI(
        model_name=model_name,
        api_key=api_key,
        provider=provider,
        base_url=base_url
    )


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a Lambda response dict.

    Args:
        status_code: HTTP status code
        body: Response body dict

    Returns:
        Lambda response dict with proper headers
    """
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization,X-Provider,X-Base-URL",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
        },
        "body": json.dumps(body)
    }


def handle_options() -> Dict[str, Any]:
    """Handle CORS preflight requests."""
    return create_response(200, {})


def handle_error(error: Exception) -> Dict[str, Any]:
    """
    Handle exceptions and return error response.

    Args:
        error: Exception that occurred

    Returns:
        Lambda error response
    """
    return create_response(500, {"error": str(error)})
