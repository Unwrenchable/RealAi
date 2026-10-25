"""Workspace inspection plugin (promoted from RealAi-unified 763a4c2,
plugins/workspace_info_plugin.py). Status: PARTIAL, opt-in plugin.

Read-only. Paths are confined to REALAI_HOME and scans are capped.

This plugin exposes a small, safe capability for inspecting a workspace root
and returning metadata that is useful for local agent workflows.
"""

import os
import re

from modules.organs.synthetic_organs import _iter_files, realai_home, within_home
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
    for path in _iter_files(root):
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
        home = realai_home()
        root = Path(path).expanduser().resolve() if path else home
        if not within_home(root, home):
            return {"plugin": "workspace_info", "ok": False, "error": "path outside REALAI_HOME", "path": str(root)}
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
            "plugin": "workspace_info",
            "ok": True,
            "path": str(root),
            "exists": root.exists(),
            "is_dir": root.is_dir(),
            "include_files": include_files,
            "entries": entries,
            "catalog": catalog,
        }

    if model is not None:
        setattr(model, "workspace_info", workspace_info)

    metadata = {
        "name": "workspace_info",
        "ok": True,
        "status": "PARTIAL",
        "version": "0.1",
        "capabilities": ["workspace_info"],
        "methods": ["workspace_info"],
        "description": "Inspect a workspace path and return basic metadata",
    }

    return metadata


def workspace_catalog(root: Optional[str] = None, max_items: int = 10) -> Dict[str, Any]:
    """Standalone catalog (backs POST /v1/workspace/catalog when opted in)."""
    home = os.path.realpath(str(realai_home()))
    cand = os.path.realpath(os.path.expanduser(root)) if root else home
    # Normalize + prefix check before any filesystem access (CodeQL py/path-injection).
    if cand != home and not cand.startswith(home + os.sep):
        return {"ok": False, "error": "root must be an existing directory inside REALAI_HOME", "root": cand}
    if not cand.startswith(home):
        return {"ok": False, "error": "root must be an existing directory inside REALAI_HOME", "root": cand}
    base = Path(cand)
    if not base.is_dir():
        return {"ok": False, "error": "root must be an existing directory inside REALAI_HOME", "root": cand}
    out = _build_catalog(base, max_items=max_items)
    out.update({"ok": True, "root": str(base)})
    out.update(_story_view(out))
    return out


def _story_view(catalog: Dict[str, Any]) -> Dict[str, Any]:
    """RealAi-unified's snapshot/story/buckets shape, derived from live's highlights.

    Additive: ``summary``/``highlights`` are unchanged; upstream callers that read
    ``snapshot``/``story``/``buckets`` keep working.
    """
    items = list(catalog.get("highlights") or [])
    summary = catalog.get("summary") or {}
    buckets: Dict[str, List[Dict[str, Any]]] = {"priority": [], "tests": [], "repair": [], "other": []}
    for it in items:
        notes = it.get("notes") or []
        if "repair-like wording" in notes:
            buckets["repair"].append(it)
        elif "test-like path" in notes or "/test" in it.get("path", ""):
            buckets["tests"].append(it)
        elif it.get("score", 0) >= 4:
            buckets["priority"].append(it)
        else:
            buckets["other"].append(it)
    return {
        "snapshot": {
            "files_considered": summary.get("files_scanned", len(items)),
            "top_weight": summary.get("top_score", items[0].get("score", 0) if items else 0),
        },
        "story": [{"path": it.get("path"), "weight": it.get("score", 0), "notes": it.get("notes", [])} for it in items[:10]],
        "buckets": {k: v[:8] for k, v in buckets.items()},
    }


def invoke(ability: str, payload: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if ability == "health":
        return {"plugin": "workspace-info", "result": {"status": "ok"}}
    if ability == "catalog":
        return {"plugin": "workspace-info", "result": workspace_catalog(payload.get("root"), int(payload.get("max_items", 10)))}
    return {"plugin": "workspace-info", "error": f"unknown ability: {ability}"}
