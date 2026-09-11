"""Deep promote ability — actually runs scan + thin wire (no hallucinated success).

Invoked via:
  craft /promote deep
  craft /deep-promote
  craft /dispatch deep promote
  ability.deep_promote / hive tool execute
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ABILITY = {
    "id": "deep_promote",
    "name": "deep_promote",
    "type": "ability",
    "status": "LIVE",
    "source": "scripts/deep_promote_scan.py + scripts/deep_promote_wire.py",
    "dest": "abilities/deep_promote.py",
    "capabilities": ["deep_promote", "nested_gold", "thin_wrap", "dispatch"],
    "secrets_policy": "none",
}


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _artifact_stat(rel: str) -> dict[str, Any]:
    p = _root() / rel
    if not p.is_file():
        return {"path": rel, "exists": False}
    st = p.stat()
    return {
        "path": rel,
        "exists": True,
        "bytes": st.st_size,
        "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
    }


def _run_script(name: str, args: list[str] | None = None, timeout: int = 1800) -> dict[str, Any]:
    root = _root()
    script = root / "scripts" / name
    res: dict[str, Any] = {
        "script": name,
        "path": str(script),
        "ok": False,
    }
    if not script.is_file():
        res["error"] = f"missing:{script}"
        return res
    cmd = [sys.executable, str(script), *(args or [])]
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        res["returncode"] = completed.returncode
        res["stdout_tail"] = (completed.stdout or "")[-3000:]
        res["stderr_tail"] = (completed.stderr or "")[-1500:]
        res["ok"] = completed.returncode == 0
    except subprocess.TimeoutExpired:
        res["error"] = f"timeout>{timeout}s"
    except Exception as e:
        res["error"] = f"{type(e).__name__}:{e}"
    return res


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Run deep promote scan then wire; verify artifacts on disk."""
    ctx = dict(context or {})
    ctx.update(kwargs)
    mode = str(ctx.get("mode") or input or "full").lower().strip()
    dry_run = bool(ctx.get("dry_run") or False)
    skip_scan = mode in {"wire", "wire-only", "thin_wrap"}
    skip_wire = mode in {"scan", "scan-only", "map"}

    out: dict[str, Any] = {
        "ok": False,
        "ability": "deep_promote",
        "mode": mode,
        "dry_run": dry_run,
        "started": datetime.now(timezone.utc).isoformat(),
        "steps": [],
        "artifacts": {},
    }

    if not skip_scan:
        step = _run_script("deep_promote_scan.py", timeout=1800)
        out["steps"].append({"name": "deep_promote_scan", "result": step})
    if not skip_wire:
        wire_args = ["--dry-run"] if dry_run else []
        step = _run_script("deep_promote_wire.py", wire_args, timeout=600)
        out["steps"].append({"name": "deep_promote_wire", "result": step})

    arts = {
        "map_md": _artifact_stat("scan_results/DEEP_PROMOTE_MAP.md"),
        "map_json": _artifact_stat("scan_results/DEEP_PROMOTE_MAP.json"),
        "queue": _artifact_stat("scan_results/deep_promote_queue.json"),
        "wire_log": _artifact_stat("scan_results/DEEP_PROMOTE_WIRE_LOG.json"),
        "status": _artifact_stat("scan_results/DEEP_PROMOTE_STATUS.md"),
    }
    out["artifacts"] = arts

    steps_ok = all(s["result"].get("ok") for s in out["steps"]) if out["steps"] else False
    arts_ok = arts["map_md"]["exists"] and arts["queue"]["exists"]
    if not skip_wire:
        arts_ok = arts_ok and arts["wire_log"]["exists"]
    out["ok"] = bool(steps_ok and arts_ok)
    out["summary"] = (
        f"deep_promote mode={mode} steps_ok={steps_ok} artifacts_ok={arts_ok} "
        f"map_bytes={arts['map_md'].get('bytes')} queue_bytes={arts['queue'].get('bytes')}"
    )
    # surface wire counts if present
    wire_log = _root() / "scan_results" / "DEEP_PROMOTE_WIRE_LOG.json"
    if wire_log.is_file():
        try:
            wl = json.loads(wire_log.read_text(encoding="utf-8"))
            actions = wl.get("actions") or []
            out["wire_actions"] = len(actions)
            out["wire_wrote"] = sum(
                1 for a in actions if a.get("action") in {"wrote", "copied"} or a.get("status") == "wrote"
            )
        except Exception:
            pass
    return out
