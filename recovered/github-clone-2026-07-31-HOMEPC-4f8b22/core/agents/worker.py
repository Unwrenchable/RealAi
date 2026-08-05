"""Worker agent."""

import json

from core.agents.base import Agent, AgentContext
from core.agents.safety import AgentSafety
from core.inference.registry import InferenceRegistry
from core.logging.logger import log
from core.metrics.metrics import AGENT_STEPS
from core.tools.registry import ToolRegistry
from core.tracing.tracer import tracer


class WorkerAgent(Agent):
    name = "worker"

    def __init__(self, inference: InferenceRegistry, tools: ToolRegistry):
        self.inference = inference
        self.tools = tools
        self.safety = AgentSafety()

    def step(self, messages, context):
        with tracer.start_as_current_span("agent.step"):
            AGENT_STEPS.inc()
            context = context if isinstance(context, dict) else {}
            allowed_tools = [tool.name for tool in self.tools.list()]
            allowed_permissions = context.get("allowed_permissions")
            if not isinstance(allowed_permissions, list):
                allowed_permissions = []
                for tool in self.tools.list():
                    allowed_permissions.extend(getattr(tool, "permissions", []))
                context["allowed_permissions"] = sorted(set(allowed_permissions))

            tool_call = context.get("tool_call")
            if tool_call:
                self.safety.validate_tool_call(tool_call, allowed_tools)
                result = self.tools.execute_tool(
                    tool_call["name"],
                    tool_call.get("arguments", {}),
                    context=context,
                )
                output = {"result": result, "used_tool": tool_call["name"]}
                log("agent.step", {"tool": tool_call["name"]})
                return output

            backend = self.inference.get_chat(context["model"])
            response = backend.generate([message.dict() if hasattr(message, "dict") else message for message in messages])
            tool_call = _extract_tool_call(response)
            if tool_call:
                self.safety.validate_tool_call(tool_call, allowed_tools)
                result = self.tools.execute_tool(
                    tool_call["name"],
                    tool_call.get("arguments", {}),
                    context=context,
                )
                output = {"result": result, "used_tool": tool_call["name"]}
                log("agent.step", {"tool": tool_call["name"]})
                return output
            log("agent.step", {"tool": None})
            return {"response": response}


def _extract_tool_call(response):
    choices = response.get("choices", [])
    if not choices:
        return None
    message = choices[0].get("message", {})
    raw = message.get("tool_call")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return None
    return None
