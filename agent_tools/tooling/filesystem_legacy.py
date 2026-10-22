from __future__ import annotations

from pathlib import Path
from typing import Any

from .registry import ToolDefinition


def get_tool_definition() -> ToolDefinition:
    return ToolDefinition(
        name="filesystem",
        description="Read files or list directories (workspace + REALAI_EXTRA_READ_ROOTS)",
        input_schema={"required": ["operation", "path"]},
        output_schema={"required": ["ok", "result"]},
        safety="guarded",
        handler=_handle_filesystem,
    )


def _resolve(path: str) -> tuple[Path | None, str | None]:
    """Resolve path under REALAI_WORKSPACE / EXTRA_READ roots when available."""
    raw = str(path or ".").strip() or "."
    try:
        from realai.workspace import realai_workspace, safe_under_read

        return safe_under_read(realai_workspace(), raw)
    except Exception:
        p = Path(raw).expanduser()
        if not p.is_absolute():
            p = (Path.cwd() / p).resolve()
        else:
            p = p.resolve()
        return p, None


def _handle_filesystem(payload: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    operation = str(payload["operation"])
    target, err = _resolve(str(payload["path"]))
    if err or target is None:
        return {"ok": False, "result": err or "bad path"}

    if dry_run:
        return {"ok": True, "result": f"DRY_RUN: would run {operation} on {target}"}

    if operation == "read":
        if not target.exists() or not target.is_file():
            return {"ok": False, "result": "file not found"}
        try:
            text = target.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            return {"ok": False, "result": str(e)}
        return {"ok": True, "result": text[:8000], "path": str(target), "truncated": len(text) > 8000}

    if operation == "list":
        if not target.exists() or not target.is_dir():
            return {"ok": False, "result": []}
        try:
            names = sorted(item.name for item in target.iterdir())
        except OSError as e:
            return {"ok": False, "result": str(e)}
        return {"ok": True, "result": names[:500], "path": str(target)}

    return {"ok": False, "result": f"unknown operation: {operation}"}
