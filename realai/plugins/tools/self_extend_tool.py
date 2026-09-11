"""Self-extend tool — propose capability growth using catalog + doctor."""
from __future__ import annotations

from typing import Any, Dict, Optional


def run(arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    arguments = arguments or {}
    goal = str(arguments.get("goal") or arguments.get("input") or "raise ability coverage").strip()
    out: Dict[str, Any] = {"ok": False, "tool": "self_extend", "goal": goal, "steps": []}
    try:
        from realai.ability_catalog import build_catalog, coverage_summary, save_catalog
        from realai.doctor import run_doctor

        before = coverage_summary()
        path = str(save_catalog(build_catalog()))
        after = coverage_summary()
        doc = run_doctor(json_mode=True)
        fails = [c for c in (doc.get("checks") or []) if not c.get("ok")]

        cat = build_catalog()
        gaps = [
            a
            for a in (cat.get("abilities") or [])
            if (a.get("status") or "") not in ("LIVE",)
        ][:8]

        out["steps"] = [
            f"saved_catalog:{path}",
            f"coverage:{(before.get('coverage') or {}).get('weighted_pct')}% -> "
            f"{(after.get('coverage') or {}).get('weighted_pct')}%",
            f"doctor_ok={doc.get('ok')} fails={len(fails)}",
        ]
        out["coverage_before"] = before.get("coverage")
        out["coverage_after"] = after.get("coverage")
        out["doctor_fails"] = fails[:5]
        out["next_abilities"] = [
            {"id": g.get("id"), "status": g.get("status"), "live_path": g.get("live_path")}
            for g in gaps
        ]
        out["plan"] = [
            "Wire PARTIAL abilities to live HTTP/tools handlers",
            "Run multi_agent_run on hard product tasks",
            "Keep REALAI_SELF_IMPROVE=true for evaluate/export",
            f"Focus goal: {goal}",
        ]
        out["ok"] = True
        out["summary"] = (
            f"Self-extend: coverage "
            f"{(before.get('coverage') or {}).get('weighted_pct')}% → "
            f"{(after.get('coverage') or {}).get('weighted_pct')}%; "
            f"{len(gaps)} abilities still not LIVE."
        )
    except Exception as e:
        out["error"] = str(e)
    return out
