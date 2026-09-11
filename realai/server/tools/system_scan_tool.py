"""System scan tool — structure scan of workspace or install."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

_SKIP = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "recovered",
    ".next",
    "dist",
    "build",
}


def run(arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    arguments = arguments or {}
    try:
        from realai.workspace import realai_home, realai_workspace

        home = realai_home()
        ws = realai_workspace()
    except Exception:
        home = Path(os.environ.get("REALAI_HOME") or Path(__file__).resolve().parents[2])
        ws = Path(os.environ.get("REALAI_WORKSPACE") or Path.cwd())

    raw = str(arguments.get("path") or ".").strip() or "."
    # Default: workspace; allow "home" keyword; optional EXTRA_READ roots
    if raw.lower() in ("home", "$home", "install"):
        root = home
    else:
        try:
            from realai.workspace import safe_under_read

            resolved, err = safe_under_read(ws, raw)
            if err or resolved is None:
                # also allow install home
                try:
                    home_p = home.resolve()
                    cand = Path(raw).expanduser().resolve() if Path(raw).is_absolute() else (home / raw).resolve()
                    cand.relative_to(home_p)
                    root = cand
                except Exception:
                    return {"ok": False, "error": err or f"path outside workspace/home: {raw}"}
            else:
                root = resolved
        except Exception:
            root = (ws / raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve()
            try:
                root.relative_to(ws.resolve())
            except Exception:
                try:
                    root.relative_to(home.resolve())
                except Exception:
                    return {"ok": False, "error": f"path outside workspace/home: {raw}"}

    if not root.exists():
        return {"ok": False, "error": f"not found: {root}"}

    files = 0
    dirs = 0
    by_ext: Dict[str, int] = {}
    top: List[Dict[str, Any]] = []
    issues: List[str] = []

    if root.is_file():
        return {
            "ok": True,
            "path": str(root),
            "type": "file",
            "size": root.stat().st_size,
        }

    for child in sorted(root.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if child.name in _SKIP:
            continue
        if child.name.startswith(".") and child.name not in (".env.example", ".gitignore"):
            continue
        entry = {
            "name": child.name,
            "type": "dir" if child.is_dir() else "file",
        }
        if child.is_file():
            entry["size"] = child.stat().st_size
            files += 1
            ext = child.suffix.lower() or "(none)"
            by_ext[ext] = by_ext.get(ext, 0) + 1
        else:
            dirs += 1
        top.append(entry)

    # shallow walk counts
    total_files = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP]
        total_files += len(filenames)
        if total_files > 5000:
            issues.append("truncated_walk_at_5000_files")
            break

    markers = {
        "package.json": (root / "package.json").is_file(),
        "pyproject.toml": (root / "pyproject.toml").is_file(),
        "requirements.txt": (root / "requirements.txt").is_file(),
        "README": any((root / n).is_file() for n in ("README.md", "README")),
        ".git": (root / ".git").exists(),
        "realai_package": (root / "realai" / "__init__.py").is_file(),
    }

    return {
        "ok": True,
        "path": str(root),
        "top_level": top[:80],
        "top_dirs": dirs,
        "top_files": files,
        "approx_total_files": total_files,
        "by_ext_top": dict(sorted(by_ext.items(), key=lambda x: -x[1])[:15]),
        "markers": markers,
        "issues": issues,
        "home": str(home),
        "workspace": str(ws),
    }
