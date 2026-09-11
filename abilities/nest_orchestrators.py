"""List nest orchestrator salvage under scripts/exportable (thin index ability)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

ABILITY = {
    "id": "nest_orchestrators",
    "name": "nest_orchestrators",
    "type": "ability",
    "status": "CODE",
    "source": "scripts/exportable/orchestrator_*.py",
    "dest": "abilities/nest_orchestrators.py",
    "capabilities": ["nest_orchestrators", "exportable", "promote"],
    "secrets_policy": "none",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    exportable = root / "scripts" / "exportable"
    files = sorted(p.name for p in exportable.glob("orchestrator_*.py"))
    return {
        "ok": True,
        "ability": "nest_orchestrators",
        "exportable_dir": str(exportable),
        "orchestrators": files,
        "note": "Relative-import salvage — adapt before promoting into core/orchestration",
        "index_doc": "modules/orchestrators/NEST_ORCHESTRATORS.md",
    }
