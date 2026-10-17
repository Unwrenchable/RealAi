"""Hive hardened tool executor — wraps ``realai.tools.SecureToolExecutor``.

Adds:
  - deterministic routing to specialist / ability / registry handlers
  - approval_store gate for dangerous / requires_confirmation tools
  - uniform error envelopes
  - specialist tool fallbacks from ``core.agents.tools``
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

HIGH_RISK = frozenset(
    {
        "dangerous",
        "restricted",
    }
)


_APPROVAL_STATE = threading.local()


def _load_approval_store() -> Any:
    """The shared approvals store module. Falls back to loading the dependency-free file by path when the
    ``realai.plugins.tools`` package __init__ cannot import (it pulls server-only deps)."""
    try:
        from realai.plugins.tools import approval_store as store

        return store
    except Exception as pkg_exc:
        import importlib.util
        from pathlib import Path

        path = Path(__file__).resolve().parents[2] / "plugins" / "tools" / "approval_store.py"
        try:
            spec = importlib.util.spec_from_file_location("_realai_approval_store_by_path", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            return mod
        except Exception as file_exc:
            raise RuntimeError(f"approvals store unavailable (package: {pkg_exc!r}; file {path}: {file_exc!r})")


def _approval_confirm(tool_name: str, arguments: Dict[str, Any]) -> bool:
    """Create a pending approval and deny until a human approves it (deny by default).

    Passes only when ``approval_id`` names an approved request for this same tool. The model-supplied
    ``approved=True`` shortcut is ignored unless REALAI_APPROVAL_TRUST_FLAG=1 (default off), because any caller,
    including the model, could set it. Never denies silently: the outcome (filed request id, or the reason the
    store could not be reached) is recorded and surfaced by ``execute_secure``.
    """
    import os

    _APPROVAL_STATE.info = info = {}
    trust_flag = os.environ.get("REALAI_APPROVAL_TRUST_FLAG", "").strip() == "1"
    if trust_flag and arguments.get("approved") is True:
        return True
    try:
        store = _load_approval_store()
        approval_id = arguments.get("approval_id")
        if approval_id:
            item = store.get_request(str(approval_id))
            ok = bool(item and item.get("status") == "approved"
                      and (item.get("payload") or {}).get("tool") in (None, tool_name))
            if not ok:
                info.update(approval_id=str(approval_id),
                            approval_status=(item or {}).get("status", "not_found"),
                            approval_error="approval_id is not an approved request for this tool")
            return ok
        item = store.create_request(
            action=f"tool:{tool_name}",
            payload={"tool": tool_name, "arguments": {k: v for k, v in arguments.items() if k != "approved"}},
        )
        info.update(approval_id=item.get("id"), approval_status="pending")
    except Exception as exc:
        logger.warning("hive_executor: approval request for %s not filed: %s", tool_name, exc)
        info.update(approval_status="error", approval_error=f"approval request not filed: {exc}")
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

    _APPROVAL_STATE.info = {}
    result = ex.execute(
        tool_name,
        args,
        h,
        confirm_callback=_approval_confirm,
    )
    if not isinstance(result, dict):
        result = {"output": result}
    approval = getattr(_APPROVAL_STATE, "info", None) or {}
    if approval and "not confirmed" in str(result.get("error") or ""):
        result.update(approval)
        if approval.get("approval_status") == "pending":
            result["status"] = "pending_approval"
            result["error"] = (f"approval required: request {approval.get('approval_id')} filed; "
                               "a human must approve it in the approval UI, then retry with approval_id")
        elif approval.get("approval_error"):
            result["error"] = approval["approval_error"]
    result.setdefault("ok", result.get("status") == "success")
    result.setdefault("envelope", "hive_executor")
    result.setdefault("tool", tool_name)
    return result
