"""Professional output formatting for the Hive CLI."""
from __future__ import annotations

import json
import sys
from typing import Any, Iterable, Mapping, Optional, Sequence


def emit_json(obj: Any, *, file=None) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True, default=str), file=file or sys.stdout)


def kv(key: str, value: Any, *, width: int = 12) -> str:
    return f"{key:<{width}} {value}"


def section(title: str) -> str:
    return f"\n{title}\n{'-' * len(title)}"


def table(rows: Sequence[Sequence[Any]], headers: Optional[Sequence[str]] = None) -> str:
    """Simple fixed-width table (no external deps)."""
    data: list[list[str]] = []
    if headers:
        data.append([str(h) for h in headers])
    for row in rows:
        data.append(["" if c is None else str(c) for c in row])
    if not data:
        return ""
    widths = [max(len(r[i]) for r in data) for i in range(len(data[0]))]
    lines: list[str] = []
    for idx, row in enumerate(data):
        line = "  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))
        lines.append(line)
        if idx == 0 and headers:
            lines.append("  ".join("-" * w for w in widths))
    return "\n".join(lines)


def error(message: str, *, hint: Optional[str] = None, detail: Optional[str] = None) -> None:
    print(f"error: {message}", file=sys.stderr)
    if hint:
        print(f"  hint: {hint}", file=sys.stderr)
    if detail:
        print(f"  detail: {detail}", file=sys.stderr)


def ok_line(message: str) -> None:
    print(f"ok: {message}")


def truncate(text: str, n: int = 120) -> str:
    text = (text or "").replace("\n", " ").strip()
    if len(text) <= n:
        return text
    return text[: n - 1] + "…"
