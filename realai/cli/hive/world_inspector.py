"""
RealAI world-model inspector — read-only view of persistent hive knowledge.

Looks at in-process world_model first, then JSON artifacts under the product tree.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def _candidates(workspace: Path) -> List[Path]:
    return [
        workspace / "realai" / "world_model.json",
        workspace / "world_model" / "world_model.json",
        workspace / "scripts" / "realai" / "world_model" / "world_model.json",
        workspace / "config" / "world_model.json",
    ]


def load_world(workspace: Path) -> Dict[str, Any]:
    # In-process
    try:
        from realai import world_model as wm

        if hasattr(wm, "WORLD_STATE"):
            state = wm.WORLD_STATE
            if callable(state):
                state = state()
            return {"ok": True, "source": "realai.world_model.WORLD_STATE", "data": state}
        if hasattr(wm, "get_state"):
            return {"ok": True, "source": "realai.world_model.get_state", "data": wm.get_state()}
        if hasattr(wm, "load"):
            return {"ok": True, "source": "realai.world_model.load", "data": wm.load()}
    except Exception as e:
        module_err = str(e)
    else:
        module_err = None

    for path in _candidates(workspace):
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return {"ok": True, "source": str(path), "data": data}
        except Exception as e:
            return {"ok": False, "source": str(path), "error": str(e)}

    # Directory of fragments
    wdir = workspace / "world_model"
    if wdir.is_dir():
        files = sorted([p for p in wdir.glob("*.json") if p.is_file()])[:20]
        if files:
            return {
                "ok": True,
                "source": str(wdir),
                "data": {"files": [str(p.relative_to(workspace)).replace("\\", "/") for p in files]},
                "note": module_err,
            }

    return {
        "ok": False,
        "error": module_err or "world model not found",
        "searched": [str(p) for p in _candidates(workspace)],
    }


def summarize(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = payload.get("data")
    if isinstance(data, dict):
        keys = list(data.keys())
        return {
            "ok": payload.get("ok"),
            "source": payload.get("source"),
            "key_count": len(keys),
            "keys": keys[:50],
            "sample": {k: data[k] for k in keys[:5]},
        }
    # WorldState / object with attributes
    if data is not None and hasattr(data, "__dict__"):
        attrs = {
            k: getattr(data, k)
            for k in dir(data)
            if not k.startswith("_") and not callable(getattr(data, k, None))
        }
        # prefer public attrs only
        keys = list(attrs.keys())[:50]
        return {
            "ok": payload.get("ok"),
            "source": payload.get("source"),
            "type": type(data).__name__,
            "key_count": len(keys),
            "keys": keys,
            "sample": {k: attrs[k] for k in keys[:5]},
        }
    return {
        "ok": payload.get("ok"),
        "source": payload.get("source"),
        "type": type(data).__name__,
        "preview": str(data)[:500],
    }


def query_world(payload: Dict[str, Any], query: str, *, limit: int = 40) -> Dict[str, Any]:
    q = (query or "").strip().lower()
    data = payload.get("data")
    hits: List[Dict[str, Any]] = []
    if not q:
        return {"ok": False, "error": "empty query", "hits": []}
    if isinstance(data, dict):
        for k, v in data.items():
            blob = f"{k}={v}".lower()
            if q in blob:
                hits.append({"key": k, "value": v if not isinstance(v, (dict, list)) else str(v)[:300]})
            if len(hits) >= limit:
                break
    return {
        "ok": True,
        "query": query,
        "source": payload.get("source"),
        "hit_count": len(hits),
        "hits": hits,
    }
