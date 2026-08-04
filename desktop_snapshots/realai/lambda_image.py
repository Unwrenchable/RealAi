"""
Lambda handler for image generation.

Handles:
- POST /v1/images/generations

Minimal dependencies: requests
"""

import json
from typing import Dict, Any
from lambda_core_shared import get_model_from_event, create_response, handle_options, handle_error


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for image generation.

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

        if path != "/v1/images/generations":
            return create_response(404, {"error": "Not found"})

        # Parse request body
        body = {}
        if event.get("body"):
            try:
                body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
            except json.JSONDecodeError:
                return create_response(400, {"error": "Invalid JSON"})

        return handle_image_generation(event, body)

    except Exception as e:
        return handle_error(e)


def handle_image_generation(event: Dict[str, Any], body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle POST /v1/images/generations."""
    model = get_model_from_event(event)

    response = model.generate_image(
        prompt=body.get("prompt", ""),
        size=body.get("size", "1024x1024"),
        quality=body.get("quality", "standard"),
        n=body.get("n", 1)
    )

    return create_response(200, response)
