"""Map product + extra workspaces to Universe worlds."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional


_SKIP_DIR = {
    ".git",
    "__pycache__",
    "node_modules",
    ".venv",
    "venv",
    "_quarantine",
    ".tox",
}


def primary_workspace(workspace: Optional[Path] = None) -> Path:
    if workspace is not None:
        return Path(workspace)
    for key in ("REALAI_WORKSPACE", "REALAI_PRODUCT_ROOT", "REALAI_ROOT"):
        raw = (os.environ.get(key) or "").strip()
        if raw:
            p = Path(raw)
            if p.is_dir():
                return p
    return Path(r"C:\RealAI-clean")


def _extra_roots() -> List[Path]:
    out: List[Path] = []
    raw = (os.environ.get("REALAI_EXTRA_WORKSPACES") or "").strip()
    if not raw:
        raw = (os.environ.get("REALAI_REPO_PATHS") or "").strip()
    for part in raw.replace(",", ";").split(";"):
        part = part.strip()
        if not part:
            continue
        p = Path(part)
        if p.is_dir():
            out.append(p)
    return out


def list_worlds(workspace: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Each mapped root is a world. Primary workspace is world 0."""
    ws = primary_workspace(workspace)
    worlds: List[Dict[str, Any]] = []
    seen = set()

    def add(root: Path, kind: str) -> None:
        try:
            key = str(root.resolve())
        except OSError:
            key = str(root)
        if key in seen:
            return
        seen.add(key)
        worlds.append(
            {
                "id": f"world-{len(worlds)}",
                "name": root.name or str(root),
                "path": str(root),
                "kind": kind,
                "exists": root.is_dir(),
            }
        )

    add(ws, "primary")
    for extra in _extra_roots():
        add(extra, "extra")

    # Nested project-like folders under primary (shallow) as sub-worlds when multi on
    try:
        multi = int(os.environ.get("REALAI_MULTI_WS") or "0")
    except ValueError:
        multi = 0
    if multi >= 2 and ws.is_dir():
        for child in sorted(ws.iterdir()):
            if not child.is_dir():
                continue
            if child.name in _SKIP_DIR or child.name.startswith("."):
                continue
            # Only treat known product siblings as worlds, not every folder
            if child.name.lower() in {
                "realai",
                "agents",
                "apps",
                "packages",
                "scripts",
                "training",
                "memory",
                "models",
                "providers",
            }:
                add(child, "subsystem")

    return worlds