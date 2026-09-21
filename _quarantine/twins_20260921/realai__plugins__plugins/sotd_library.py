"""
Shot of the Day library growth + variety.

RealAI owns the *catalog* and *selection logic*.
RackUp may pass history of shown shot IDs; RealAI also keeps an optional
local JSON growth file under REALAI_DATA_DIR (not the NestJS DB).
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Optional


def _data_dir() -> Path:
    base = os.environ.get("REALAI_DATA_DIR") or os.path.join(
        os.path.expanduser("~"), ".realai"
    )
    p = Path(base) / "rackup_coach"
    p.mkdir(parents=True, exist_ok=True)
    return p


def library_path() -> Path:
    return _data_dir() / "sotd_library.json"


def history_path() -> Path:
    return _data_dir() / "sotd_history.json"


def load_grown_shots() -> list[dict[str, Any]]:
    path = library_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data.get("shots") or [])
    except Exception:
        return []


def save_grown_shot(shot: dict[str, Any]) -> dict[str, Any]:
    """Append a community/learned shot definition (provider-local growth)."""
    path = library_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"shots": []}
    except Exception:
        data = {"shots": []}
    shots = list(data.get("shots") or [])
    sid = shot.get("id") or f"grown-{int(time.time())}"
    shot = {**shot, "id": sid, "grown_at": time.time()}
    # de-dupe by id
    shots = [s for s in shots if s.get("id") != sid]
    shots.append(shot)
    data["shots"] = shots[-500:]  # cap
    data["updated_at"] = time.time()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return {"ok": True, "id": sid, "count": len(data["shots"]), "path": str(path)}


def record_shown(
    player_id: str,
    shot_id: str,
    *,
    meta: Optional[dict[str, Any]] = None,
) -> None:
    path = history_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except Exception:
        data = {}
    key = str(player_id or "anon")
    hist = list(data.get(key) or [])
    hist.append({"shot_id": shot_id, "ts": time.time(), **(meta or {})})
    data[key] = hist[-100:]
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def recently_shown(player_id: str, limit: int = 14) -> list[str]:
    path = history_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        hist = list(data.get(str(player_id)) or [])
        return [h.get("shot_id") for h in hist[-limit:] if h.get("shot_id")]
    except Exception:
        return []


def variety_penalty(shot_id: str, recent_ids: list[str]) -> float:
    """Higher = worse (recently shown)."""
    if not recent_ids:
        return 0.0
    pen = 0.0
    for i, rid in enumerate(reversed(recent_ids)):
        if rid == shot_id:
            # More recent → heavier penalty
            pen += 20.0 - i * 1.2
    return max(0.0, pen)


def growth_policy() -> dict[str, Any]:
    return {
        "static_catalog": "plugins/rackup_coach/abilities/shot_of_the_day.py _SHOT_LIBRARY",
        "grown_catalog": str(library_path()),
        "player_history": str(history_path()),
        "rules": [
            "Prefer shots matching weaknesses + Pyramid rack size + skill band",
            "Penalize shot IDs shown to this player in last ~14 deliveries",
            "Always include why_this_shot (regular-play improvement, not trick novelty)",
            "RackUp may pass payload.shown_shot_ids to enforce variety across devices",
            "RackUp may call ability sotd_contribute to grow library with coach-approved shots",
            "RealAI stores growth under REALAI_DATA_DIR; RackUp DB is source of truth for what was shown in-app",
        ],
        "max_grown_shots": 500,
        "history_per_player": 100,
    }
