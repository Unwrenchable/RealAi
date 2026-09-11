import json
from typing import Dict, Any
from lambda_core_shared import get_model_from_event, create_response, handle_options, handle_error

class RealAIAgent:
    def __init__(self):
        self.models = {}

    def handler(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
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
                return self.handle_options()

            path = event.get("path", "")
            method = event.get("httpMethod", "POST")

            if method != "POST":
                return self.create_response(405, {"error": "Method not allowed"})

            # Parse request body
            body = {}
            if event.get("body"):
                try:
                    body = json.loads(event["body"]) if isinstance(event["body"], str) else event["body"]
                except json.JSONDecodeError:
                    return self.create_response(400, {"error": "Invalid JSON"})

            # Route to appropriate handler
            if path == "/v1/reasoning/chain":
                return self.handle_reasoning_chain(event, body)
            elif path == "/v1/synthesis/knowledge":
                return self.handle_synthesis_knowledge(event, body)
            elif path == "/v1/reflection/analyze":
                return self.handle_reflection_analyze(event, body)
            elif path == "/v1/agents/orchestrate":
                return self.handle_agents_orchestrate(event, body)

            return self.create_response(404, {"error": "Not found"})

        except Exception as e:
            return self.handle_error(e)

    def handle_options(self) -> Dict[str, Any]:
        """
        Handle CORS preflight request.
        """
        return self.create_response(200, {})

    def handle_reasoning_chain(self, event: Dict[str, Any], body: Dict[str, Any]) -> Dict[str, Any]:
        """Handle POST /v1/reasoning/chain."""
        model_name = event.get("model_name")
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")

        model = self.models[model_name]

        response = model.chain_of_thought(
            problem=body.get("problem", ""),
            domain=body.get("domain")
        )

        return self.create_response(200, response)

    def handle_synthesis_knowledge(self, event: Dict[str, Any], body: Dict[str, Any]) -> Dict[str, Any]:
        """Handle POST /v1/synthesis/knowledge."""
        model_name = event.get("model_name")
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")

        model = self.models[model_name]

        response = model.synthesize_knowledge(
            topics=body.get("topics", []),
            output_format=body.get("output_format", "narrative")
        )

        return self.create_response(200, response)

    def handle_reflection_analyze(self, event: Dict[str, Any], body: Dict[str, Any]) -> Dict[str, Any]:
        """Handle POST /v1/reflection/analyze."""
        model_name = event.get("model_name")
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")

        model = self.models[model_name]

        response = model.self_reflect(
            interaction_history=body.get("interaction_history"),
            focus=body.get("focus", "general")
        )

        return self.create_response(200, response)

    def handle_agents_orchestrate(self, event: Dict[str, Any], body: Dict[str, Any]) -> Dict[str, Any]:
        """Handle POST /v1/agents/orchestrate."""
        model_name = event.get("model_name")
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")

        model = self.models[model_name]

        response = model.orchestrate_agents(
            task=body.get("task", ""),
            agent_roles=body.get("agent_roles")
        )

        return self.create_response(200, response)

    def create_response(self, status_code: int, data: Dict[str, Any] = None, error: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a response with the given status code and data.

        Args:
            status_code: HTTP status code
            data: Response data
            error: Error message

        Returns:
            Response dict
        """
        response = {"statusCode": status_code}
        if data:
            response["body"] = data
        if error:
            response["body"] = error
        return response

    def handle_error(self, e: Exception) -> Dict[str, Any]:
        """
        Handle an error.

        Args:
            e: Exception

        Returns:
            Error response dict
        """
        error = {"error": str(e)}
        return self.create_response(500, error=error)


def get_model_from_event(event: Dict[str, Any]) -> "RealAIAgent":
    """
    Get a model from the event.

    Args:
        event: Lambda event dict

    Returns:
        RealAIAgent model
    """
    model_name = event.get("model_name")
    if model_name:
        return RealAIAgent()
    else:
        raise ValueError("Model not found")


if __name__ == "__main__":
    agent = RealAIAgent()
    event = {
        "httpMethod": "POST",
        "path": "/v1/reasoning/chain",
        "body": '{"problem": "What is the meaning of life?", "domain": "philosophy"}'
    }
    print(agent.handler(event, None))