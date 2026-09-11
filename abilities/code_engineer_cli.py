"""Thin wrap over ``realai.plugins.tools.code_engineer_cli``."""

from __future__ import annotations

import importlib
from typing import Any

ABILITY = {
    "id": "code_engineer_cli",
    "name": "code_engineer_cli",
    "type": "ability",
    "status": "CODE",
    "source": "realai.plugins.tools.code_engineer_cli",
    "dest": "abilities/code_engineer_cli.py",
    "capabilities": ["code_engineer", "patch", "cli"],
    "secrets_policy": "none",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or input or "status").strip().lower() or "status"

    # Live agent class check (no patch required for status)
    agent = None
    agent_ok = False
    agent_err = None
    try:
        import sys
        from pathlib import Path

        root = Path(__file__).resolve().parents[1]
        root_s = str(root)
        if root_s in sys.path:
            sys.path.remove(root_s)
        sys.path.insert(0, root_s)
        # Prefer product-root agent_tools over realai/agent_tools shadow
        try:
            from realai.v3_runtime_bridge import _ensure_product_agent_tools

            _ensure_product_agent_tools()
        except Exception:
            pass
        from agent_tools.agents_impl.code_engineer_agent import CodeEngineerAgent

        agent = CodeEngineerAgent(repo_root=Path(".").resolve())
        agent_ok = True
    except Exception as e:
        agent = None
        agent_ok = False
        agent_err = f"{type(e).__name__}:{e}"

    patch = str(ctx.get("patch") or ctx.get("patch_text") or ctx.get("diff") or "").strip()
    if action in {"status", "info", ""} or not patch:
        return {
            "ok": agent_ok,
            "ability": "code_engineer_cli",
            "action": "status",
            "agent_class": "CodeEngineerAgent" if agent_ok else None,
            "repo_root": str(getattr(agent, "repo_root", "")) if agent_ok else None,
            "error": agent_err,
            "hint": "Pass patch/patch_text + commit_message (+ dry_run=true) to validate/apply",
            "cli": "python -m realai.plugins.tools.code_engineer_cli --help",
        }

    if not agent_ok or agent is None:
        return {"ok": False, "ability": "code_engineer_cli", "error": agent_err}

    msg = str(ctx.get("commit_message") or ctx.get("message") or "chore: code_engineer_cli apply").strip()
    dry = bool(ctx.get("dry_run", True))
    try:
        result = agent.apply_patch_and_commit(patch_text=patch, commit_message=msg, dry_run=dry)
        return {
            "ok": bool(result.get("ok")),
            "ability": "code_engineer_cli",
            "dry_run": dry,
            "result": result,
        }
    except Exception as e:
        return {"ok": False, "ability": "code_engineer_cli", "error": str(e)}
