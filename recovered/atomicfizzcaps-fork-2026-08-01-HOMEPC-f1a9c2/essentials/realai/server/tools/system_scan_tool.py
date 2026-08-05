"""
system_scan_tool — recovered capability surface.

No historical file named system_scan_tool.py found under Users\\tsmit.
Wraps desktop missing-gold scan + recovery inventory for system/gold scans.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def scan(kind: str = "recovery") -> Dict[str, Any]:
    """
    kind:
      recovery — recovery_registry inventory
      desktop — run scan_desktop_missing_gold.py summary from last map
      abilities — ability catalog coverage
    """
    out: Dict[str, Any] = {"tool": "system_scan_tool", "kind": kind}
    if kind == "recovery":
        try:
            from realai.recovery_registry import inventory
            out["result"] = inventory()
            out["status"] = "ok"
        except Exception as e:
            out["status"] = "error"
            out["error"] = str(e)
        return out

    if kind == "desktop":
        from pathlib import Path
        import json
        p = Path(__file__).resolve().parents[3] / "scan_results" / "desktop_missing_gold_map.json"
        if p.is_file():
            data = json.loads(p.read_text(encoding="utf-8"))
            out["result"] = {
                "hits": data.get("hit_count"),
                "staged": data.get("staged_count"),
                "p0_live_miss": data.get("p0_missing_from_live_realai_pkg"),
                "path": str(p),
            }
            out["status"] = "ok"
        else:
            out["status"] = "missing_scan"
            out["hint"] = "POST /v1/self-heal/discover {mode:desktop}"
        return out

    if kind == "abilities":
        try:
            from realai.ability_catalog import coverage_summary
            out["result"] = coverage_summary()
            out["status"] = "ok"
        except Exception as e:
            out["status"] = "error"
            out["error"] = str(e)
        return out

    out["status"] = "error"
    out["error"] = f"unknown kind {kind}"
    return out


def run(arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    arguments = arguments or {}
    return scan(str(arguments.get("kind") or "recovery"))
