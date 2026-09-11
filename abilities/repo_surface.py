"""Repo-level authority map — where packages live and how to import them."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

ABILITY = {
    "id": "repo_surface",
    "name": "repo_surface",
    "type": "ability",
    "status": "LIVE",
    "source": "C:\\RealAI-clean layout",
    "dest": "abilities/repo_surface.py",
    "capabilities": ["authority", "layout", "levels", "twins"],
    "secrets_policy": "none",
}

_ROOT = Path(__file__).resolve().parents[1]
_SCAN = _ROOT / "scan_results" / "repo_levels_authority.json"

AUTHORITY = {
    "abilities": {"path": "abilities/", "import": "abilities", "level": "repo_root"},
    "modules": {"path": "modules/", "import": "modules", "level": "repo_root"},
    "agent_tools": {"path": "agent_tools/", "import": "agent_tools", "level": "repo_root"},
    "agents": {"path": "agents/", "import": "agents", "level": "repo_root", "note": "hive JSON in .github/agents; richer code also under realai/agents"},
    "core": {"path": "realai/core/", "import": "core", "level": "package"},
    "orchestration": {"path": "realai/orchestration/", "import": "realai.orchestration", "level": "package", "http": ":8001"},
    "plugins": {"path": "realai/plugins/", "import": "realai.plugins", "level": "package"},
    "personas": {"path": "personas/", "level": "repo_root"},
    "console": {"path": "console.html", "level": "repo_root"},
    "world_model_json": {"path": "world_model.json", "level": "repo_root"},
    "models_weights": {
        "path": r"C:\models\checkpoints_lora",
        "level": "external",
        "env": ["REALAI_MODELS_DIR", "REALAI_LORA_ROOT"],
        "note": "GGUF + LoRA + datasets; repo models/ is manifests only",
    },
    "models_manifests": {"path": "models/", "level": "repo_root", "note": "cards/registry only — weights live under C:\\models\\checkpoints_lora"},
    "gold": {"path": "archive/gold/", "level": "archive", "note": "reference packs; runtime already in agent_tools / realai/core / realai/orchestration"},
    "archive": {"path": "archive/, recovered/, imports/, _quarantine/", "level": "archive"},
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or "list").lower().strip()

    persisted = {}
    if _SCAN.is_file():
        try:
            persisted = json.loads(_SCAN.read_text(encoding="utf-8"))
        except Exception:
            persisted = {}

    if action in {"list", "map", "authority", "status", ""}:
        return {
            "ok": True,
            "ability": "repo_surface",
            "root": str(_ROOT),
            "authority": AUTHORITY,
            "last_level_fix": {
                "manifest": str(_SCAN) if _SCAN.is_file() else None,
                "moved": len((persisted.get("moved") or [])),
                "generated_at": persisted.get("generated_at"),
            },
            "pythonpath_hint": ["C:\\\\RealAI-clean", "C:\\\\RealAI-clean\\\\realai"],
            "note": (
                "Repo root holds import homes for abilities/modules/agent_tools/agents. "
                "Package realai/ holds core/orchestration/plugins/bot/cli. "
                "Identical wrong-level twins were quarantined under _quarantine/repo_levels_20260830."
            ),
        }

    name = str(ctx.get("name") or input or "").strip()
    if action == "where" and name:
        key = name.lower().replace("\\", "/").strip("/")
        hit = AUTHORITY.get(key)
        if hit:
            return {"ok": True, "name": key, **hit}
        # fuzzy
        for k, v in AUTHORITY.items():
            if key in k or key in str(v.get("path") or "") or key in str(v.get("import") or ""):
                return {"ok": True, "name": k, **v}
        return {"ok": False, "error": f"unknown:{name}", "known": sorted(AUTHORITY)}

    return {
        "ok": False,
        "error": f"unknown_action:{action}",
        "actions": ["list", "where"],
        "known": sorted(AUTHORITY),
    }
