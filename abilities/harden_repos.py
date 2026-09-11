"""Thin wrap over ``realai.plugins.tools.harden_repos``."""

from __future__ import annotations

import importlib
from typing import Any

ABILITY = {
    "id": "harden_repos",
    "name": "harden_repos",
    "type": "ability",
    "status": "CODE",
    "source": "realai.plugins.tools.harden_repos",
    "dest": "abilities/harden_repos.py",
    "capabilities": ["repos", "harden", "security"],
    "secrets_policy": "none",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    try:
        mod = importlib.import_module("realai.plugins.tools.harden_repos")
    except Exception as e:
        return {
            "ok": False,
            "ability": "harden_repos",
            "source": ABILITY["source"],
            "error": f"{type(e).__name__}:{e}",
        }
    result = {
        "main": hasattr(mod, "main"),
        "hint": "CLI module — invoke via python -m realai.plugins.tools.harden_repos",
        "exports": [n for n in dir(mod) if not n.startswith("_")][:40],
    }
    return {"ok": True, "ability": "harden_repos", "source": ABILITY["source"], "result": result}
