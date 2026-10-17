"""Single source of truth for the approvals store path (stdlib only, safe to import anywhere).

One file is shared by the approval UI (``realai.plugins.tools.approval_ui``), the approval gate
(``realai.core.approval_gate``), ``hive_executor`` and the read-only ``approval_status`` hive tool.

Resolution order:
  1. env ``REALAI_APPROVALS_STORE`` or ``APPROVALS_STORE``
  2. ``config/approvals.json`` (or the file named by ``REALAI_APPROVALS_CONFIG``):
     ``"store"`` on Windows, ``"store_posix"`` elsewhere
  3. default: ``C:\\RealAI-clean\\.approvals.json`` on Windows; a temp-dir store elsewhere (box/CI)

Tests pin the store to a temp file via ``tests/conftest.py`` on every OS, so a test run never touches the
live queue. ``self_data`` keeps its own sandbox store (``realai.hive_tools.approvals``).
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

WINDOWS_DEFAULT = r"C:\RealAI-clean\.approvals.json"
_REPO = Path(__file__).resolve().parents[2]


def _config() -> dict:
    p = Path(os.environ.get("REALAI_APPROVALS_CONFIG") or (_REPO / "config" / "approvals.json"))
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def store_path() -> Path:
    env = (os.environ.get("REALAI_APPROVALS_STORE") or os.environ.get("APPROVALS_STORE") or "").strip()
    if env:
        return Path(env)
    cfg = _config()
    key = "store" if os.name == "nt" else "store_posix"
    if str(cfg.get(key) or "").strip():
        return Path(str(cfg[key]))
    if os.name == "nt":
        return Path(WINDOWS_DEFAULT)
    return Path(tempfile.gettempdir()) / "realai-approvals" / ".approvals.json"
