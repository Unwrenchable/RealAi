"""Hive hardened tool executor — wraps ``realai.tools.SecureToolExecutor``.

Adds:
  - deterministic routing to specialist / ability / registry handlers
  - approval_store gate for dangerous / requires_confirmation tools
  - uniform error envelopes
  - specialist tool fallbacks from ``core.agents.tools``
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

HIGH_RISK = frozenset(
    {
        "dangerous",
        "restricted",
    }
)


def _approval_confirm(tool_name: str, arguments: Dict[str, Any]) -> bool:
    """Create a pending approval and deny until explicitly approved.

    Auto-approve only when arguments contain ``approved=True`` or
    ``approval_id`` pointing at an approved request.
    """
    try:
        from realai.plugins.tools import approval_store as store
    except Exception:
        # If approval store missing, deny high-risk by default
        return bool(arguments.get("approved") is True)

    if arguments.get("approved") is True:
        return True
    approval_id = arguments.get("approval_id")
    if approval_id:
        item = store.get_request(str(approval_id))
        return bool(item and item.get("status") == "approved")

    # Create pending request for human review
    store.create_request(
        action=f"tool:{tool_name}",
        payload={"tool": tool_name, "arguments": arguments},
    )
    return False


def _resolve_handler(tool_name: str) -> Optional[Callable[..., Any]]:
    # 1) specialist tools
    try:
        from core.agents.tools import TOOL_REGISTRY as SPEC_TOOLS

        fn = SPEC_TOOLS.get(tool_name)
        if fn is not None:
            def _spec(**kwargs: Any) -> Any:
                drop = {
                    "approved",
                    "approval_id",
                    "force_approve",
                    "action",
                    "tool",
                    "tool_name",
                    "arguments",
                }
                clean = {k: v for k, v in kwargs.items() if k not in drop}
                if hasattr(fn, "invoke"):
                    # langchain StructuredTool: prefer dict, else first value
                    try:
                        return fn.invoke(clean)
                    except Exception:
                        if len(clean) == 1:
                            return fn.invoke(next(iter(clean.values())))
                        raise
                return fn(**clean) if clean else fn()

            return _spec
    except Exception:
        pass

    # 2) ability module run()
    try:
        import importlib

        mod = importlib.import_module(f"abilities.{tool_name}")
        if hasattr(mod, "run"):
            return lambda **kwargs: mod.run(context=kwargs, **kwargs)
    except Exception:
        pass

    # 3) rackup ability package
    try:
        import importlib

        mod = importlib.import_module(f"abilities.rackup.{tool_name}")
        if hasattr(mod, "run"):
            return lambda **kwargs: mod.run(context=kwargs, **kwargs)
    except Exception:
        pass

    # 4) v3 bridge registry tool
    try:
        from realai.v3_runtime_bridge import execute_registry_tool

        return lambda **kwargs: execute_registry_tool(tool_name, kwargs)
    except Exception:
        pass
    return None


def _ensure_hive_schemas() -> None:
    """Register specialist + rackup tools so validator accepts hive-routed names."""
    from realai.tools import TOOL_REGISTRY, ToolSchema

    TOOL_REGISTRY.ensure_ability_catalog_loaded()
    extras = {
        "web_research": "Research query tool",
        "code_execution": "Execute code in a sandbox",
        "math_solver": "Solve a math problem",
        "creative_writer": "Creative writing helper",
        "data_analyzer": "Analyze structured data",
        "image_processor": "Describe or process image requests",
        "task_automator": "Turn a task into executable steps",
        "knowledge_synthesizer": "Synthesize notes into knowledge",
        "self_reflector": "Critic / self-reflection",
        "pyramid": "RackUp pyramid rules",
        "roc": "RackUp rating convert (ROC)",
        "glicko2": "RackUp Glicko-2 rating update",
        "money_audit": "RackUp ledger / money audit",
    }
    for name, desc in extras.items():
        if TOOL_REGISTRY.get(name) is not None:
            continue
        TOOL_REGISTRY.register(
            ToolSchema(
                name=name,
                description=desc,
                parameters={"type": "object", "additionalProperties": True},
                required=[],
                safety_level="restricted" if name in {"code_execution", "task_automator"} else "safe",
                source="hive_specialist",
            )
        )


_EXECUTOR: Any = None


def get_executor() -> Any:
    global _EXECUTOR
    from realai.tools import TOOL_REGISTRY, SecureToolExecutor

    _ensure_hive_schemas()
    if _EXECUTOR is None:
        _EXECUTOR = SecureToolExecutor(TOOL_REGISTRY)
    return _EXECUTOR


def execute_secure(
    tool_name: str,
    arguments: Optional[Dict[str, Any]] = None,
    *,
    handler: Optional[Callable[..., Any]] = None,
    force_approve: bool = False,
) -> Dict[str, Any]:
    """Execute a tool through SecureToolExecutor with hive routing + approval."""
    args = dict(arguments or {})
    if force_approve:
        args["approved"] = True

    ex = get_executor()
    h = handler or _resolve_handler(tool_name)
    if h is None:
        return {
            "status": "error",
            "ok": False,
            "error": f"no_handler:{tool_name}",
            "envelope": "hive_executor",
        }

    # Mark high-risk tools as requiring confirmation via schema if present
    try:
        schema = ex._registry.get(tool_name)
        if schema is not None and schema.safety_level in HIGH_RISK:
            schema.requires_confirmation = True
    except Exception:
        pass

    result = ex.execute(
        tool_name,
        args,
        h,
        confirm_callback=_approval_confirm,
    )
    if not isinstance(result, dict):
        result = {"output": result}
    result.setdefault("ok", result.get("status") == "success")
    result.setdefault("envelope", "hive_executor")
    result.setdefault("tool", tool_name)
    return result
