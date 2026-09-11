"""Universe memory hook — reports env + on-disk memory presence (no runtime)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict


def memory_status(workspace: Path) -> Dict[str, Any]:
    flag = (os.environ.get("REALAI_MEMORY") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    paths = [
        workspace / "realai" / "memory",
        workspace / "memory",
        Path(os.environ.get("REALAI_HOME") or "") / "memory" if os.environ.get("REALAI_HOME") else None,
    ]
    found = []
    for p in paths:
        if p is None:
            continue
        if p.is_dir():
            found.append(str(p))

    active = flag or bool(found)
    return {
        "active": active,
        "label": "active" if active else "inactive",
        "env_REALAI_MEMORY": os.environ.get("REALAI_MEMORY"),
        "paths": found,
        "note": "static bridge — does not start a vector engine",
    }