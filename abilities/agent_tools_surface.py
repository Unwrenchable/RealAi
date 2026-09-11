"""Unified agent_tools surface — living package on PYTHONPATH.

Authority: repo-root ``agent_tools`` (imported as ``agent_tools``).
``realai/agent_tools`` is a near-twin; prefer root package.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

ABILITY = {
    "id": "agent_tools_surface",
    "name": "agent_tools_surface",
    "type": "ability",
    "status": "LIVE",
    "source": "agent_tools/ + realai/agent_tools/",
    "dest": "abilities/agent_tools_surface.py",
    "capabilities": [
        "filesystem",
        "http",
        "crypto",
        "solana",
        "memory",
        "profiles",
        "executor",
        "overmind",
    ],
    "secrets_policy": "solana/crypto default dry_run",
}

_ROOT = Path(__file__).resolve().parents[1]
_TOP = _ROOT / "agent_tools"
_PKG = _ROOT / "realai" / "agent_tools"

LIVE_TOOLS = {
    "status": {"role": "Package + registry status", "dispatch": "status"},
    "list_tools": {"role": "List wired tooling registry", "dispatch": "list_tools"},
    "list_agents": {"role": "List agent_tools + agentx agents", "dispatch": "list_agents"},
    "list_profiles": {"role": "Access profiles", "dispatch": "list_profiles"},
    "filesystem": {"role": "Filesystem tool", "dispatch": "invoke", "tool": "filesystem"},
    "http": {"role": "HTTP tool", "dispatch": "invoke", "tool": "http"},
    "crypto": {"role": "Crypto tool", "dispatch": "invoke", "tool": "crypto"},
    "solana": {"role": "Solana tool (dry_run default)", "dispatch": "invoke", "tool": "solana"},
    "memory": {"role": "agent_tools memory module", "dispatch": "memory"},
    "overmind": {"role": "Overmind runner in agent_tools", "dispatch": "overmind"},
    "assess": {"role": "Assess agent vs profile", "dispatch": "assess"},
}


def _tree_info(path: Path) -> Dict[str, Any]:
    if not path.is_dir():
        return {"path": str(path), "exists": False}
    dirs = sorted(p.name for p in path.iterdir() if p.is_dir() and p.name != "__pycache__")
    files = sorted(p.name for p in path.iterdir() if p.is_file())
    return {
        "path": str(path),
        "exists": True,
        "dirs": dirs,
        "files": files,
        "file_count": len(files),
        "dir_count": len(dirs),
    }


def _inventory() -> Dict[str, Any]:
    status = {}
    try:
        from realai.v3_runtime_bridge import agent_tools_status

        status = agent_tools_status()
    except Exception as e:
        status = {"ok": False, "error": str(e)}
    tools = {}
    try:
        from realai.v3_runtime_bridge import list_agent_tools_tools

        tools = list_agent_tools_tools()
    except Exception as e:
        tools = {"ok": False, "error": str(e)}
    return {
        "ok": True,
        "ability": "agent_tools_surface",
        "unified": True,
        "authority": "agent_tools (repo root on PYTHONPATH)",
        "packages": {
            "agent_tools": _tree_info(_TOP),
            "realai_agent_tools": _tree_info(_PKG),
        },
        "status": status,
        "tools": tools,
        "live_tools": [
            {"id": tid, "role": meta.get("role"), "dispatch": meta.get("dispatch")}
            for tid, meta in LIVE_TOOLS.items()
        ],
        "note": "action=run tool=filesystem|http|solana|list_tools|status (dry_run default true)",
    }


def _run_tool(tool_id: str, raw_input: str = "", ctx: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ctx = dict(ctx or {})
    tid = (tool_id or "status").strip().lower().replace("-", "_")
    meta = LIVE_TOOLS.get(tid) or {"role": tool_id, "dispatch": "invoke", "tool": tid}
    dispatch = str(meta.get("dispatch") or "invoke")
    out: Dict[str, Any] = {"ok": True, "tool": tid, "role": meta.get("role"), "dispatch": dispatch}

    if dispatch == "status":
        from realai.v3_runtime_bridge import agent_tools_status

        out["result"] = agent_tools_status()
        out["via"] = "agent_tools_status"
        return out

    if dispatch == "list_tools":
        from realai.v3_runtime_bridge import list_agent_tools_tools

        out["result"] = list_agent_tools_tools()
        out["via"] = "list_agent_tools_tools"
        return out

    if dispatch == "list_agents":
        from realai.v3_runtime_bridge import list_agent_tools_agents

        out["result"] = list_agent_tools_agents(
            limit=int(ctx.get("limit") or 50),
            query=str(ctx.get("query") or raw_input or ""),
        )
        out["via"] = "list_agent_tools_agents"
        return out

    if dispatch == "list_profiles":
        from realai.v3_runtime_bridge import list_access_profiles

        out["result"] = list_access_profiles()
        out["via"] = "list_access_profiles"
        return out

    if dispatch == "assess":
        from realai.v3_runtime_bridge import assess_agent_profile

        out["result"] = assess_agent_profile(
            str(ctx.get("agent_id") or raw_input or ""),
            str(ctx.get("profile") or "balanced"),
        )
        out["via"] = "assess_agent_profile"
        return out

    if dispatch == "invoke":
        from realai.v3_runtime_bridge import invoke_agent_tool

        tool = str(meta.get("tool") or tid)
        payload = ctx.get("payload") if isinstance(ctx.get("payload"), dict) else {}
        if raw_input and "path" not in payload and tool == "filesystem":
            payload = {**payload, "operation": payload.get("operation") or "list", "path": raw_input or "."}
        if raw_input and "url" not in payload and tool == "http":
            payload = {**payload, "url": raw_input}
        dry_run = bool(ctx.get("dry_run") if ctx.get("dry_run") is not None else True)
        out["result"] = invoke_agent_tool(
            tool,
            payload=payload,
            profile=str(ctx.get("profile") or "balanced"),
            dry_run=dry_run,
        )
        out["via"] = f"invoke_agent_tool:{tool}"
        out["dry_run"] = dry_run
        return out

    if dispatch == "memory":
        try:
            import agent_tools.memory as mem

            out["result"] = {
                "ok": True,
                "module": "agent_tools.memory",
                "exports": [n for n in dir(mem) if not n.startswith("_")][:40],
            }
            out["via"] = "agent_tools.memory"
        except Exception as e:
            out["ok"] = False
            out["error"] = str(e)
        return out

    if dispatch == "overmind":
        try:
            from realai.v3_runtime_bridge import execute_registry_tool

            out["result"] = execute_registry_tool(
                "ability.overmind_runner",
                {"input": raw_input or str(ctx.get("goal") or "status"), "context": ctx},
            )
            out["via"] = "ability.overmind_runner"
        except Exception as e:
            out["ok"] = False
            out["error"] = str(e)
        return out

    out["ok"] = False
    out["error"] = f"unknown_dispatch:{dispatch}"
    return out


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or "list").lower().strip()
    tool = str(ctx.get("tool") or ctx.get("id") or ctx.get("name") or "").strip()

    if action in {"list", "inventory", "status", "registry", "map", ""}:
        inv = _inventory()
        if tool:
            inv["selected"] = LIVE_TOOLS.get(tool.lower()) or {"id": tool}
        return inv

    if action in {"run", "invoke", "dispatch"}:
        raw = str(input or "")
        if not tool and raw:
            parts = raw.split(None, 1)
            tool = parts[0]
            raw = parts[1] if len(parts) > 1 else ""
        if not tool:
            tool = "status"
        return _run_tool(tool, raw_input=raw, ctx=ctx)

    return {
        "ok": False,
        "error": f"unknown_action:{action}",
        "actions": ["list", "run"],
        "known": sorted(LIVE_TOOLS.keys()),
    }
