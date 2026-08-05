"""Scoped file I/O tool."""

from pathlib import Path
from typing import Any, Dict

from core.tools.base import Tool
from core.tools.permissions import Permissions


class FileTool(Tool):
    name = "file_tool"
    description = "Read/write files in scoped workspace"
    params_schema = {
        "action": {"type": "string", "enum": ["read", "write"]},
        "path": {"type": "string"},
        "content": {"type": "string"},
    }
    permissions = [Permissions.FILESYSTEM]

    def __init__(self, scope_dir: str = "."):
        self.scope_dir = Path(scope_dir).resolve()

    def _resolve_path(self, relative_path: str) -> Path:
        candidate = (self.scope_dir / relative_path).resolve()
        if not str(candidate).startswith(str(self.scope_dir)):
            raise ValueError("Path escapes tool scope.")
        return candidate

    def __call__(self, **kwargs: Any) -> Dict[str, Any]:
        action = str(kwargs.get("action", "read"))
        rel_path = str(kwargs.get("path", "")).strip()
        if not rel_path:
            raise ValueError("path is required")
        target = self._resolve_path(rel_path)
        if action == "read":
            return {"content": target.read_text(encoding="utf-8") if target.exists() else ""}
        if action == "write":
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(str(kwargs.get("content", "")), encoding="utf-8")
            return {"status": "ok"}
        raise ValueError("Unsupported action")
