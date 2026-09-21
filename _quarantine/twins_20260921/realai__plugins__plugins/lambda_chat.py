"""
Lambda handler for chat and text completions.

Handles:
- POST /v1/chat/completions
- POST /v1/completions

Minimal dependencies: requests, beautifulsoup4
"""

import json
from typing import Dict, Any
from lambda_core_shared import get_model_from_event, create_response, handle_options, handle_error


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for chat and text completions.

    Args:
        event: Lambda event dict
        context: Lambda context object

    Returns:
        Lambda response dict
    """
    try:
        # Handle CORS preflight
        if event.get("httpMethod") == "OPTIONS":
            return handle_options()

        path = event.get("path", "")
        method = event.get("httpMethod", "POST")

        if method != "POST":
            return create_response(405, {"error": "Method not allowed"})

        # Parse request body
        body = {}
        if event.get("body"):
            try:
                body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
            except json.JSONDecodeError:
                return create_response(400, {"error": "Invalid JSON"})

        # Route to appropriate handler
        if path == "/v1/chat/completions":
            return handle_chat_completions(event, body)
        elif path == "/v1/completions":
            return handle_completions(event, body)

        return create_response(404, {"error": "Not found"})

    except Exception as e:
        return handle_error(e)


def handle_chat_completions(event: Dict[str, Any], body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle POST /v1/chat/completions."""
    model = get_model_from_event(event)

    response = model.chat_completion(
        messages=body.get("messages", []),
        temperature=body.get("temperature", 0.7),
        max_tokens=body.get("max_tokens"),
        stream=body.get("stream", False)
    )

    return create_response(200, response)


def handle_completions(event: Dict[str, Any], body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle POST /v1/completions."""
    model = get_model_from_event(event)

    response = model.text_completion(
        prompt=body.get("prompt", ""),
        temperature=body.get("temperature", 0.7),
        max_tokens=body.get("max_tokens")
    )

    return create_response(200, response)
