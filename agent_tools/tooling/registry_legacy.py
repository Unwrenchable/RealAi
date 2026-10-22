from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from typing import Any, Callable


@dataclass(slots=True)
class ToolDefinition:
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    safety: str
    handler: Callable[[dict[str, Any], bool], dict[str, Any]]


class ToolRegistry:
    def __init__(self, tools: dict[str, ToolDefinition]) -> None:
        self._tools = tools

    @classmethod
    def auto_wire(cls) -> "ToolRegistry":
        tools: dict[str, ToolDefinition] = {}
        # Prefer top-level agent_tools; fall back to realai.agent_tools_gold
        module_bases = ("agent_tools.tooling", "realai.agent_tools_gold.tooling")
        for module_name in ("http", "filesystem", "crypto", "solana"):
            last_err: Exception | None = None
            definition = None
            for base in module_bases:
                try:
                    module = import_module(f"{base}.{module_name}")
                    definition = module.get_tool_definition()
                    break
                except Exception as e:
                    last_err = e
            if definition is None:
                raise ImportError(
                    f"Could not load tool module {module_name}: {last_err}"
                ) from last_err
            tools[definition.name] = definition
        return cls(tools)

    def list_tools(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def get(self, tool_name: str) -> ToolDefinition | None:
        return self._tools.get(tool_name)

    def invoke(
        self,
        tool_name: str,
        payload: dict[str, Any],
        allowed_tools: list[str],
        dry_run: bool,
    ) -> dict[str, Any]:
        if tool_name not in self._tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        if tool_name not in allowed_tools and "*" not in allowed_tools:
            raise PermissionError(f"Tool '{tool_name}' is not allowed for this agent")

        tool = self._tools[tool_name]
        _validate_payload(payload, tool.input_schema)
        output = tool.handler(payload, dry_run)
        _validate_payload(output, tool.output_schema)
        return output


def _validate_payload(payload: dict[str, Any], schema: dict[str, Any]) -> None:
    required = schema.get("required", [])
    if not isinstance(required, list):
        raise ValueError("schema.required must be a list")
    for key in required:
        if key not in payload:
            raise ValueError(f"Missing required key '{key}'")
