"""
RealAI Unified Tool-Calling Protocol
=====================================
Provides ToolSchema, ToolRegistry, ToolCallValidator, and ToolCallOptimizer.

Usage::

    from realai.tools import TOOL_REGISTRY, ToolCallValidator

    tools = TOOL_REGISTRY.to_openai_format()
    result = ToolCallValidator().validate("web_research", {"query": "test"})
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolSchema:
    """Schema definition for a callable tool.

    Attributes:
        name: Unique tool name.
        description: Human-readable description.
        parameters: JSON Schema object describing parameters.
        required: List of required parameter names.
        safety_level: One of "safe", "restricted", "dangerous".
    """
    name: str
    description: str
    parameters: Dict[str, Any]
    required: List[str]
    safety_level: str = "safe"


@dataclass
class ValidationResult:
    """Result from a tool call validation.

    Attributes:
        valid: Whether the call is valid.
        errors: List of error messages.
    """
    valid: bool
    errors: List[str] = field(default_factory=list)


class ToolRegistry:
    """Singleton registry of all available tools.

    Register tools with register(), retrieve with get(), and export
    to OpenAI format with to_openai_format().
    """

    def __init__(self) -> None:
        """Initialize an empty tool registry."""
        self._tools: Dict[str, ToolSchema] = {}

    def register(self, schema: ToolSchema) -> None:
        """Register a tool schema.

        Args:
            schema: The ToolSchema to register.
        """
        self._tools[schema.name] = schema

    def get(self, name: str) -> Optional[ToolSchema]:
        """Retrieve a tool schema by name.

        Args:
            name: Tool name to look up.

        Returns:
            ToolSchema or None if not found.
        """
        return self._tools.get(name)

    def list_all(self) -> List[ToolSchema]:
        """Return all registered tool schemas.

        Returns:
            List of all ToolSchema objects.
        """
        return list(self._tools.values())

    def to_openai_format(self) -> List[Dict[str, Any]]:
        """Export tools in OpenAI tools array format.

        Returns:
            List of tool dicts compatible with OpenAI API.
        """
        result = []
        for schema in self._tools.values():
            result.append({
                "type": "function",
                "function": {
                    "name": schema.name,
                    "description": schema.description,
                    "parameters": schema.parameters,
                },
            })
        return result


class ToolCallValidator:
    """Validates tool calls against registered schemas.

    Checks tool existence, required fields, and type matching.
    """

    _TYPE_MAP = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    def validate(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> ValidationResult:
        """Validate a tool call.

        Args:
            tool_name: Name of the tool to call.
            arguments: Arguments dict for the call.

        Returns:
            ValidationResult with valid flag and errors list.
        """
        errors = []
        schema = TOOL_REGISTRY.get(tool_name)
        if schema is None:
            return ValidationResult(valid=False, errors=["Unknown tool: {0}".format(tool_name)])

        # Check required fields
        for req in schema.required:
            if req not in arguments:
                errors.append("Missing required field: {0}".format(req))

        # Check types
        props = schema.parameters.get("properties", {})
        for arg_name, arg_value in arguments.items():
            if arg_name in props:
                expected_type = props[arg_name].get("type")
                if expected_type and expected_type in self._TYPE_MAP:
                    expected = self._TYPE_MAP[expected_type]
                    if not isinstance(arg_value, expected):
                        errors.append(
                            "Field '{0}' expected {1}, got {2}".format(
                                arg_name, expected_type, type(arg_value).__name__
                            )
                        )

        return ValidationResult(valid=len(errors) == 0, errors=errors)


class ToolCallOptimizer:
    """Optimizes batches of tool calls.

    Provides deduplication and parallel batching.
    """

    def deduplicate(self, calls: List[Dict]) -> List[Dict]:
        """Remove exact-duplicate tool calls.

        Args:
            calls: List of tool call dicts.

        Returns:
            Deduplicated list preserving order.
        """
        seen = set()
        result = []
        for call in calls:
            # Serialize to a stable string for comparison
            key = (call.get("name", ""), str(sorted(call.get("arguments", {}).items())))
            if key not in seen:
                seen.add(key)
                result.append(call)
        return result

    def batch_parallel(self, calls: List[Dict]) -> List[List[Dict]]:
        """Group independent calls into parallel batches.

        Currently groups all calls into a single batch (conservative approach
        — no dependency analysis).

        Args:
            calls: List of tool call dicts.

        Returns:
            List of batches, each batch is a list of independent calls.
        """
        if not calls:
            return []
        # Simple strategy: each unique tool name gets its own group
        groups: Dict[str, List[Dict]] = {}
        for call in calls:
            name = call.get("name", "unknown")
            if name not in groups:
                groups[name] = []
            groups[name].append(call)
        return list(groups.values())


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------

TOOL_REGISTRY = ToolRegistry()

# ---------------------------------------------------------------------------
# Built-in tool registrations
# ---------------------------------------------------------------------------

TOOL_REGISTRY.register(ToolSchema(
    name="web_research",
    description="Search the web for information on a given query.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The search query."},
            "max_results": {"type": "integer", "description": "Maximum results to return."},
        },
    },
    required=["query"],
    safety_level="safe",
))

TOOL_REGISTRY.register(ToolSchema(
    name="execute_code",
    description="Execute a code snippet in a sandboxed environment.",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Code to execute."},
            "language": {"type": "string", "description": "Programming language."},
        },
    },
    required=["code"],
    safety_level="restricted",
))

TOOL_REGISTRY.register(ToolSchema(
    name="generate_image",
    description="Generate an image from a text prompt.",
    parameters={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Image generation prompt."},
            "size": {"type": "string", "description": "Image dimensions, e.g. 1024x1024."},
        },
    },
    required=["prompt"],
    safety_level="safe",
))

TOOL_REGISTRY.register(ToolSchema(
    name="translate",
    description="Translate text to a target language.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to translate."},
            "target_language": {"type": "string", "description": "Target language code."},
        },
    },
    required=["text", "target_language"],
    safety_level="safe",
))

TOOL_REGISTRY.register(ToolSchema(
    name="transcribe_audio",
    description="Transcribe audio from a file path or URL.",
    parameters={
        "type": "object",
        "properties": {
            "audio_path": {"type": "string", "description": "Path or URL to audio file."},
            "language": {"type": "string", "description": "Optional language hint."},
        },
    },
    required=["audio_path"],
    safety_level="safe",
))
