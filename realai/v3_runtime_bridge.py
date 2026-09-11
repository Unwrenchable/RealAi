"""Package-root import shim for the v3 runtime bridge.

Craft, hive banner, and orchestrator import ``realai.v3_runtime_bridge``.
Gold lives at ``realai.orchestration.v3_runtime_bridge`` after the 2026-08-30
package-root sort. This dest-empty module re-exports that gold. Do not put
logic here.
"""
from __future__ import annotations

from realai.orchestration.v3_runtime_bridge import (
    _agent_tools_pkg,
    _ensure_product_agent_tools,
    agent_tools_status,
    assess_agent_profile,
    execute_registry_tool,
    hive_agents_status,
    invoke_agent_tool,
    list_access_profiles,
    list_agent_tools_agents,
    list_agent_tools_tools,
    orch_health,
    route_model,
    run_multi_agent,
    tools_catalog,
    vulkan_health,
    workspace_tool,
)

__all__ = [
    "_agent_tools_pkg",
    "_ensure_product_agent_tools",
    "agent_tools_status",
    "assess_agent_profile",
    "execute_registry_tool",
    "hive_agents_status",
    "invoke_agent_tool",
    "list_access_profiles",
    "list_agent_tools_agents",
    "list_agent_tools_tools",
    "orch_health",
    "route_model",
    "run_multi_agent",
    "tools_catalog",
    "vulkan_health",
    "workspace_tool",
]