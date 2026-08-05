"""Tool registry."""

from typing import Any, Dict

from core.tools.base import Tool
from core.logging.logger import log
from core.metrics.metrics import TOOL_CALLS
from core.tracing.tracer import tracer


class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        self.tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        if name not in self.tools:
            raise KeyError("Unknown tool: {0}".format(name))
        return self.tools[name]

    def list(self):
        return list(self.tools.values())

    def execute_tool(self, name: str, args: Dict[str, Any], context: Dict[str, Any] = None):
        with tracer.start_as_current_span("tool.{0}".format(name)):
            tool = self.get(name)
            runtime_context = context if isinstance(context, dict) else {}
            required = list(getattr(tool, "permissions", []) or [])
            if runtime_context:
                allowed = set(runtime_context.get("allowed_permissions", []))
                for permission in required:
                    if permission not in allowed:
                        raise PermissionError("Permission denied: {0}".format(permission))
            payload = args or {}
            log("tool.call", {"tool": name, "args": payload})
            TOOL_CALLS.labels(tool=name).inc()
            result = tool(**payload, _context=runtime_context)
            log("tool.result", {"tool": name, "result": result})
            return result
