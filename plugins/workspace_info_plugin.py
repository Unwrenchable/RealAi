"""Workspace inspection plugin for local development environments.

This plugin exposes a small, safe capability for inspecting a workspace root
and returning metadata that is useful for local agent workflows.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def _build_catalog(root: Path, max_items: int = 10) -> Dict[str, Any]:
    """Scan a directory tree for likely-relevant files using lightweight heuristics."""
    ignored_dirs = {
        ".git",
        ".hg",
        ".svn",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        "dist",
        "build",
        ".next",
        ".pytest_cache",
        ".mypy_cache",
    }
    ignored_names = {".DS_Store", "Thumbs.db"}
    ignored_suffixes = {".pyc", ".pyo", ".log", ".tmp"}

    repair_markers = re.compile(r"(todo|fixme|hack|temp|wip|placeholder|rough|legacy|broken|debug|stub)", re.I)
    structure_markers = re.compile(r"(router|service|manager|state|schema|adapter|registry|workflow|plugin|memory|agent)", re.I)
    test_markers = re.compile(r"(^|/)(test|spec|fixture|mock)(/|$)", re.I)
    version_markers = re.compile(r"\b(v1|v2|v3|alpha|beta|rc)\b", re.I)
    text_suffixes = {".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml", ".md"}

    notable: List[Dict[str, Any]] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue

        rel_parts = path.parts
        if any(part in ignored_dirs for part in rel_parts):
            continue
        if path.name in ignored_names or path.suffix.lower() in ignored_suffixes:
            continue

        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        score = 0
        notes: List[str] = []
        if path.suffix.lower() in text_suffixes:
            score += 1
        if repair_markers.search(text):
            score += 3
            notes.append("repair-like wording")
        if structure_markers.search(text):
            score += 2
            notes.append("structural clues")
        if test_markers.search(rel):
            score += 1
            notes.append("test-like path")
        if version_markers.search(text):
            score += 1
            notes.append("version hints")
        if path.suffix.lower() in {".py", ".ts", ".js"} and text.strip():
            score += 1

        if score > 0:
            notable.append(
                {
                    "path": rel,
                    "score": score,
                    "notes": notes or ["general file"],
                    "kind": path.suffix.lower() or "file",
                }
            )

    notable.sort(key=lambda item: (-item["score"], item["path"]))

    highlights = notable[: max_items]
    return {
        "summary": {
            "files_scanned": len(notable),
            "top_score": notable[0]["score"] if notable else 0,
            "highlight_count": len(highlights),
        },
        "highlights": highlights,
    }


def register(model, config=None):
    """Register a workspace inspection method on the provided model."""

    def workspace_info(path=None, include_files=False, max_items: int = 10) -> Dict[str, Any]:
        root = Path(path or ".").resolve()
        entries: List[str] = []
        if include_files:
            try:
                entries = [item.name for item in sorted(root.iterdir(), key=lambda p: p.name)]
            except OSError:
                entries = []

        catalog: Optional[Dict[str, Any]] = None
        if root.exists() and root.is_dir():
            catalog = _build_catalog(root, max_items=max_items)

        return {
            "plugin": "workspace_info_plugin",
            "ok": True,
            "path": str(root),
            "exists": root.exists(),
            "is_dir": root.is_dir(),
            "include_files": include_files,
            "entries": entries,
            "catalog": catalog,
        }

    setattr(model, "workspace_info", workspace_info)

    metadata = {
        "name": "workspace_info_plugin",
        "version": "0.1",
        "capabilities": ["workspace_info"],
        "methods": ["workspace_info"],
        "description": "Inspect a workspace path and return basic metadata",
    }

    return metadata
