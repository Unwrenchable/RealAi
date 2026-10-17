"""Approval request store backed by a JSON file.

Agents create approval requests for high-risk actions (e.g. committing to
main, running deploys).  A human reviews them via the approval UI and either
approves or rejects.  Once approved the orchestrator picks up the request and
executes the corresponding action.

The store path is resolved at call time by ``realai.core.approvals_config.store_path()`` (env
``REALAI_APPROVALS_STORE`` / ``APPROVALS_STORE``, then ``config/approvals.json``, then
``C:\\RealAI-clean\\.approvals.json`` on Windows / a temp store elsewhere), so the approval UI, the gate,
``hive_executor`` and ``approval_status`` all share one file. Pass ``store_path`` to override per call.

This module is intentionally dependency-free (stdlib only) so it can be
imported without installing Flask.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4



def _resolve_store() -> Path:
    try:
        from realai.core.approvals_config import store_path

        return store_path()
    except Exception:  # loaded outside the realai package (e.g. ``from approval_store import``)
        import importlib.util

        cfg = Path(__file__).resolve().parents[2] / "core" / "approvals_config.py"
        try:
            spec = importlib.util.spec_from_file_location("_realai_approvals_config", cfg)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)  # type: ignore[union-attr]
            return mod.store_path()
        except Exception:
            env = os.getenv("REALAI_APPROVALS_STORE") or os.getenv("APPROVALS_STORE")
            if env:
                return Path(env)
            raise RuntimeError("approvals store path unresolved: set REALAI_APPROVALS_STORE")


class _StorePath:
    """Back-compat for callers that read ``approval_store._DEFAULT_STORE``: resolves on use."""

    def __fspath__(self) -> str:
        return str(_resolve_store())

    def __repr__(self) -> str:
        return repr(_resolve_store())


_DEFAULT_STORE: Any = _StorePath()


def _p(store_path: Any) -> Path:
    return _resolve_store() if store_path is None or isinstance(store_path, _StorePath) else Path(store_path)


def _load(store_path: Path | None = None) -> dict[str, Any]:
    store_path = _p(store_path)
    if not store_path.exists():
        return {"items": []}
    try:
        return json.loads(store_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"items": []}


def _save(data: dict[str, Any], store_path: Path | None = None) -> None:
    store_path = _p(store_path)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def create_request(
    action: str,
    payload: dict[str, Any],
    store_path: Path | None = None,
) -> dict[str, Any]:
    """Create a new pending approval request and return it."""
    data = _load(store_path)
    item: dict[str, Any] = {
        "id": str(uuid4()),
        "action": action,
        "payload": payload,
        "status": "pending",
    }
    data["items"].append(item)
    _save(data, store_path)
    return item


def list_requests(store_path: Path | None = None) -> list[dict[str, Any]]:
    """Return all approval requests."""
    return _load(store_path).get("items", [])


def update_request(
    req_id: str,
    status: str,
    store_path: Path | None = None,
) -> bool:
    """Update the status of a request.  Returns ``True`` if found, else ``False``."""
    data = _load(store_path)
    for item in data["items"]:
        if item["id"] == req_id:
            item["status"] = status
            _save(data, store_path)
            return True
    return False


def get_request(
    req_id: str,
    store_path: Path | None = None,
) -> dict[str, Any] | None:
    """Return a single request by ID, or ``None`` if not found."""
    for item in _load(store_path).get("items", []):
        if item["id"] == req_id:
            return item
    return None


def annotate_request(
    req_id: str,
    store_path: Path | None = None,
    **kwargs: Any,
) -> bool:
    """Merge arbitrary keyword fields into a request entry.

    Use this to attach execution results, metadata, or flags without
    touching the ``status`` field directly.  Returns ``True`` if the
    request was found, ``False`` otherwise.

    Example::

        annotate_request(req_id, executed=True, result={"ok": True, "commit_sha": "abc…"})
    """
    data = _load(store_path)
    for item in data["items"]:
        if item["id"] == req_id:
            item.update(kwargs)
            _save(data, store_path)
            return True
    return False
