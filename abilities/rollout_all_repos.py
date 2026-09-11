"""Thin wrap over ``realai.plugins.tools.rollout_all_repos``."""

from __future__ import annotations

import importlib
from typing import Any

ABILITY = {
    "id": "rollout_all_repos",
    "name": "rollout_all_repos",
    "type": "ability",
    "status": "CODE",
    "source": "realai.plugins.tools.rollout_all_repos",
    "dest": "abilities/rollout_all_repos.py",
    "capabilities": ["repos", "rollout", "web3"],
    "secrets_policy": "none",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    try:
        mod = importlib.import_module("realai.plugins.tools.rollout_all_repos")
    except Exception as e:
        return {
            "ok": False,
            "ability": "rollout_all_repos",
            "source": ABILITY["source"],
            "error": f"{type(e).__name__}:{e}",
        }
    result = {
        "main": hasattr(mod, "main"),
        "hint": "CLI module — invoke via python -m realai.plugins.tools.rollout_all_repos",
        "exports": [n for n in dir(mod) if not n.startswith("_")][:40],
    }
    return {"ok": True, "ability": "rollout_all_repos", "source": ABILITY["source"], "result": result}
