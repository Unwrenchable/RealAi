"""
Lambda handler for core API endpoints.

Handles:
- GET /
- GET /health
- GET /v1/models
- GET /v1/models/{model_id}
- GET /v1/capabilities
- GET /v1/providers/capabilities

Minimal dependencies: requests only
"""

import json
import os
from typing import Dict, Any
from lambda_core_shared import get_model_from_event, create_response, handle_options, handle_error
from realai import PROVIDER_CONFIGS


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for core API endpoints.

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
        method = event.get("httpMethod", "GET")

        # Route to appropriate handler
        if method == "GET":
            if path == "/" or path == "":
                return handle_root()
            elif path == "/health":
                return handle_health()
            elif path == "/v1/models":
                return handle_list_models()
            elif path.startswith("/v1/models/"):
                return handle_get_model(event, path)
            elif path == "/v1/capabilities":
                return handle_capabilities(event)
            elif path == "/v1/providers/capabilities":
                return handle_provider_capabilities(event)

        return create_response(404, {"error": "Not found"})

    except Exception as e:
        return handle_error(e)


def handle_root() -> Dict[str, Any]:
    """Handle GET / - serve the landing page."""
    try:
        # Try to read the index.html file
        index_path = os.path.join(os.path.dirname(__file__), "index.html")
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "text/html",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": html_content
            }
    except Exception as e:
        # Fallback to JSON response if HTML file is not found
        pass

    # Fallback JSON response
    return create_response(200, {
        "message": "RealAI deployment is live. Use /health for status.",
        "documentation": "https://github.com/Unwrenchable/realai",
        "endpoints": {
            "health": "GET /health",
            "models": "GET /v1/models",
            "capabilities": "GET /v1/capabilities",
            "chat": "POST /v1/chat/completions",
            "completions": "POST /v1/completions",
            "images": "POST /v1/images/generations",
            "videos": "POST /v1/videos/generations",
            "embeddings": "POST /v1/embeddings",
            "audio_transcription": "POST /v1/audio/transcriptions",
            "audio_speech": "POST /v1/audio/speech",
            "reasoning": "POST /v1/reasoning/chain",
            "synthesis": "POST /v1/synthesis/knowledge",
            "reflection": "POST /v1/reflection/analyze",
            "agents": "POST /v1/agents/orchestrate"
        }
    })


def handle_health() -> Dict[str, Any]:
    """Handle GET /health."""
    return create_response(200, {
        "status": "healthy",
        "model": "realai-2.0"
    })


def handle_list_models() -> Dict[str, Any]:
    """Handle GET /v1/models."""
    models = [
        {
            "id": "realai-2.0",
            "object": "model",
            "created": 1708308000,
            "owned_by": "realai",
            "permission": [],
            "root": "realai-2.0",
            "parent": None,
        }
    ]

    # Add configured provider models
    for provider_name, cfg in PROVIDER_CONFIGS.items():
        models.append({
            "id": cfg["default_model"],
            "object": "model",
            "created": 1708308000,
            "owned_by": provider_name,
            "permission": [],
            "root": cfg["default_model"],
            "parent": None,
        })

    return create_response(200, {"object": "list", "data": models})


def handle_get_model(event: Dict[str, Any], path: str) -> Dict[str, Any]:
    """Handle GET /v1/models/{model_id}."""
    model_id = path[len("/v1/models/"):]
    model = get_model_from_event(event)

    response = model.get_model_info()
    response["object"] = "model"
    response["id"] = model_id

    return create_response(200, response)


def handle_capabilities(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle GET /v1/capabilities."""
    model = get_model_from_event(event)
    return create_response(200, model.get_capability_catalog())


def handle_provider_capabilities(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle GET /v1/providers/capabilities."""
    model = get_model_from_event(event)
    query_params = event.get("queryStringParameters", {}) or {}
    provider = query_params.get("provider")

    return create_response(200, model.get_provider_capabilities(provider=provider))
