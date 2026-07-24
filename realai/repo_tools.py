"""Workspace-scoped tools so local RealAI can edit this repo (no paid APIs)."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .model_assets import repo_root


def workspace_root() -> Path:
    env = os.environ.get("REALAI_WORKSPACE", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return repo_root()


def _scoped_path(relative: str) -> Path:
    root = workspace_root()
    candidate = Path(relative).expanduser()
    if not candidate.is_absolute():
        candidate = (root / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if not str(candidate).startswith(str(root)):
        raise ValueError(f"Path escapes workspace: {relative}")
    return candidate


def read_file(
    target_file: str,
    offset: Optional[int] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    path = _scoped_path(target_file)
    if not path.is_file():
        return {"error": f"File not found: {path}"}
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    start = max((offset or 1) - 1, 0)
    end = len(lines) if limit is None else min(start + int(limit), len(lines))
    snippet = "\n".join(f"{i + 1}→{lines[i]}" for i in range(start, end))
    return {"path": str(path), "content": snippet, "total_lines": len(lines)}


def list_dir(target_directory: str = ".") -> Dict[str, Any]:
    path = _scoped_path(target_directory)
    if not path.is_dir():
        return {"error": f"Not a directory: {path}"}
    entries = []
    for child in sorted(path.iterdir()):
        if child.name.startswith("."):
            continue
        kind = "dir" if child.is_dir() else "file"
        entries.append({"name": child.name, "type": kind})
    return {"path": str(path), "entries": entries[:200]}


def grep(
    pattern: str,
    path: str = ".",
    glob: Optional[str] = None,
    head_limit: int = 40,
) -> Dict[str, Any]:
    root = _scoped_path(path)
    if root.is_file():
        search_root = root.parent
        file_filter = root.name
    else:
        search_root = root
        file_filter = None
    matches: List[str] = []
    regex = re.compile(pattern)
    for dirpath, dirnames, filenames in os.walk(search_root):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in ("node_modules", "venv", ".git")]
        for name in filenames:
            if file_filter and name != file_filter:
                continue
            if glob and not Path(name).match(glob):
                continue
            fp = Path(dirpath) / name
            try:
                if fp.stat().st_size > 2_000_000:
                    continue
                for i, line in enumerate(fp.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    if regex.search(line):
                        rel = fp.relative_to(workspace_root())
                        matches.append(f"{rel}:{i}:{line[:300]}")
                        if len(matches) >= head_limit:
                            return {"matches": matches, "truncated": True}
            except (OSError, UnicodeError):
                continue
    return {"matches": matches, "truncated": False}


def search_replace(
    file_path: str,
    old_string: str,
    new_string: str,
    replace_all: bool = False,
) -> Dict[str, Any]:
    path = _scoped_path(file_path)
    if not path.is_file():
        return {"error": f"File not found: {path}"}
    text = path.read_text(encoding="utf-8")
    if old_string not in text:
        return {"error": "old_string not found in file"}
    if replace_all:
        updated = text.replace(old_string, new_string)
    else:
        updated = text.replace(old_string, new_string, 1)
    path.write_text(updated, encoding="utf-8")
    return {"status": "ok", "path": str(path)}


def run_terminal_command(
    command: str,
    description: Optional[str] = None,
    timeout: int = 120,
) -> Dict[str, Any]:
    root = workspace_root()
    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=max(5, int(timeout)),
            encoding="utf-8",
            errors="replace",
        )
        out = (completed.stdout or "") + (completed.stderr or "")
        if len(out) > 12000:
            out = out[:12000] + "\n...[truncated]"
        return {
            "exit_code": completed.returncode,
            "output": out,
            "description": description or "",
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "output": "", "error": "timeout"}


REPO_TOOL_HANDLERS = {
    "read_file": lambda **kw: read_file(**kw),
    "list_dir": lambda **kw: list_dir(**kw),
    "grep": lambda **kw: grep(**kw),
    "search_replace": lambda **kw: search_replace(**kw),
    "run_terminal_command": lambda **kw: run_terminal_command(**kw),
}


def register_repo_tools(registry) -> None:
    """Register OpenAI-style schemas on a ToolRegistry instance."""
    from .tools import ToolSchema

    specs = [
        (
            "read_file",
            "Read a UTF-8 file in the repo (line numbers included).",
            {"target_file": {"type": "string"}, "offset": {"type": "integer"}, "limit": {"type": "integer"}},
            ["target_file"],
        ),
        (
            "list_dir",
            "List files and folders under a repo path.",
            {"target_directory": {"type": "string"}},
            [],
        ),
        (
            "grep",
            "Search file contents with a regex pattern.",
            {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
                "glob": {"type": "string"},
                "head_limit": {"type": "integer"},
            },
            ["pattern"],
        ),
        (
            "search_replace",
            "Replace text in a repo file (read the file first).",
            {
                "file_path": {"type": "string"},
                "old_string": {"type": "string"},
                "new_string": {"type": "string"},
                "replace_all": {"type": "boolean"},
            },
            ["file_path", "old_string", "new_string"],
        ),
        (
            "run_terminal_command",
            "Run a shell command in the repo root (tests, python -m, git, etc.).",
            {"command": {"type": "string"}, "description": {"type": "string"}, "timeout": {"type": "integer"}},
            ["command"],
        ),
    ]
    for name, desc, props, required in specs:
        registry.register(
            ToolSchema(
                name=name,
                description=desc,
                parameters={"type": "object", "properties": props},
                required=required,
                safety_level="restricted" if name != "read_file" and name != "list_dir" and name != "grep" else "safe",
                requires_confirmation=name in ("search_replace", "run_terminal_command"),
            )
        )