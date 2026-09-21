"""
Lambda handler for embeddings and audio.

Handles:
- POST /v1/embeddings
- POST /v1/audio/transcriptions
- POST /v1/audio/speech

Minimal dependencies: requests only (routes to external APIs)
Heavy local dependencies (sentence-transformers, vosk, pyttsx3) are NOT included.
"""

import json
from typing import Dict, Any
from lambda_core_shared import get_model_from_event, create_response, handle_options, handle_error


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for embeddings and audio.

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
        if path == "/v1/embeddings":
            return handle_embeddings(event, body)
        elif path == "/v1/audio/transcriptions":
            return handle_audio_transcriptions(event, body)
        elif path == "/v1/audio/speech":
            return handle_audio_speech(event, body)

        return create_response(404, {"error": "Not found"})

    except Exception as e:
        return handle_error(e)


def handle_embeddings(event: Dict[str, Any], body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle POST /v1/embeddings."""
    model = get_model_from_event(event)

    response = model.create_embeddings(
        input_text=body.get("input", ""),
        model=body.get("model", "realai-embeddings")
    )

    return create_response(200, response)


def handle_audio_transcriptions(event: Dict[str, Any], body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle POST /v1/audio/transcriptions."""
    model = get_model_from_event(event)

    response = model.transcribe_audio(
        audio_file=body.get("file", ""),
        language=body.get("language"),
        prompt=body.get("prompt")
    )

    return create_response(200, response)


def handle_audio_speech(event: Dict[str, Any], body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle POST /v1/audio/speech."""
    model = get_model_from_event(event)

    response = model.generate_audio(
        text=body.get("input", ""),
        voice=body.get("voice", "alloy"),
        model=body.get("model", "realai-tts")
    )

    return create_response(200, response)
