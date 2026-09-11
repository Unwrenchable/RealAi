"""
Lambda handler for advanced AI capabilities.

Handles:
- POST /v1/reasoning/chain
- POST /v1/synthesis/knowledge
- POST /v1/reflection/analyze
- POST /v1/agents/orchestrate

Minimal dependencies: requests, beautifulsoup4
"""

import json
from typing import Dict, Any
from lambda_core_shared import get_model_from_event, create_response, handle_options, handle_error


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for advanced AI capabilities.

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
        if path == "/v1/reasoning/chain":
            return handle_reasoning_chain(event, body)
        elif path == "/v1/synthesis/knowledge":
            return handle_synthesis_knowledge(event, body)
        elif path == "/v1/reflection/analyze":
            return handle_reflection_analyze(event, body)
        elif path == "/v1/agents/orchestrate":
            return handle_agents_orchestrate(event, body)

        return create_response(404, {"error": "Not found"})

    except Exception as e:
        return handle_error(e)


def handle_reasoning_chain(event: Dict[str, Any], body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle POST /v1/reasoning/chain."""
    model = get_model_from_event(event)

    response = model.chain_of_thought(
        problem=body.get("problem", ""),
        domain=body.get("domain")
    )

    return create_response(200, response)


def handle_synthesis_knowledge(event: Dict[str, Any], body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle POST /v1/synthesis/knowledge."""
    model = get_model_from_event(event)

    response = model.synthesize_knowledge(
        topics=body.get("topics", []),
        output_format=body.get("output_format", "narrative")
    )

    return create_response(200, response)


def handle_reflection_analyze(event: Dict[str, Any], body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle POST /v1/reflection/analyze."""
    model = get_model_from_event(event)

    response = model.self_reflect(
        interaction_history=body.get("interaction_history"),
        focus=body.get("focus", "general")
    )

    return create_response(200, response)


def handle_agents_orchestrate(event: Dict[str, Any], body: Dict[str, Any]) -> Dict[str, Any]:
    """Handle POST /v1/agents/orchestrate."""
    model = get_model_from_event(event)

    response = model.orchestrate_agents(
        task=body.get("task", ""),
        agent_roles=body.get("agent_roles")
    )

    return create_response(200, response)
