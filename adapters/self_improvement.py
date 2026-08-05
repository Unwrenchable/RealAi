"""Self-improvement adapter."""
from __future__ import annotations
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def self_improvement_status() -> dict[str, Any]:
    pack = ROOT / "modules" / "self_improvement"
    files = [p.name for p in pack.glob("*.py")] if pack.exists() else []
    return {
        "pack": str(pack.relative_to(ROOT)).replace("\\", "/") if pack.exists() else None,
        "modules": files,
        "living_self_improvement": (ROOT / "realai" / "self_improvement.py").exists(),
    }
