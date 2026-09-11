from __future__ import annotations

from typing import Any

try:
    from realai.plugins.tools.registry import ToolDefinition  # type: ignore
except Exception:
    try:
        from agent_tools.registry import ToolDefinition  # type: ignore
    except Exception:
        from dataclasses import dataclass
        @dataclass
        class ToolDefinition:
            name: str = 'solana'
            description: str = ''
            parameters: dict | None = None
            handler: Any = None
            def __post_init__(self):
                if self.parameters is None:
                    self.parameters = {}


def get_tool_definition() -> ToolDefinition:
    return ToolDefinition(
        name="solana",
        description="Stub Solana helper tool for orchestration planning",
        input_schema={"required": ["operation", "amount"]},
        output_schema={"required": ["ok", "message"]},
        safety="dangerous",
        handler=_handle_solana,
    )


def _handle_solana(payload: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    operation = str(payload["operation"])
    amount = payload["amount"]
    if dry_run:
        return {"ok": True, "message": f"DRY_RUN: would execute {operation} with amount {amount}"}
    return {
        "ok": False,
        "message": "Solana SDK not configured in this runtime. Install integration to enable live execution.",
    }

