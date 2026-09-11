"""Self-repair tool — diagnose stack health and apply safe fixes."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional


def run(arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    arguments = arguments or {}
    issue = str(arguments.get("issue") or arguments.get("input") or "auto").strip()
    out: Dict[str, Any] = {"ok": False, "tool": "self_repair", "issue": issue, "actions": []}
    try:
        from realai.workspace import realai_home, realai_workspace
        from realai.doctor import run_doctor

        home = realai_home()
        ws = realai_workspace()
        out["home"] = str(home)
        out["workspace"] = str(ws)

        # Ensure critical dirs
        for rel in ("logs", "logs/state", "training/data", "scan_results", "models"):
            p = home / rel
            if not p.exists():
                p.mkdir(parents=True, exist_ok=True)
                out["actions"].append(f"mkdir {rel}")

        # Env sanity
        os.environ.setdefault("REALAI_HOME", str(home))
        os.environ.setdefault("REALAI_ROOT", str(home))
        os.environ.setdefault("REALAI_DEFAULT_MODEL", "realai-default-coder")
        out["actions"].append("env defaults set")

        # Catalog refresh
        try:
            from realai.ability_catalog import build_catalog, save_catalog

            save_catalog(build_catalog())
            out["actions"].append("ability_catalog refreshed")
        except Exception as e:
            out["actions"].append(f"catalog_skip:{e}")

        # Curated promote dry path status (never force-write here)
        try:
            from realai.self_heal import status

            st = status()
            out["self_heal"] = {
                "enabled": st.get("enabled"),
                "promote_actionable": st.get("promote_actionable"),
            }
            out["actions"].append("self_heal status read")
        except Exception as e:
            out["actions"].append(f"self_heal_skip:{e}")

        doc = run_doctor(json_mode=True)
        out["doctor_ok"] = doc.get("ok")
        out["doctor_fails"] = [c for c in (doc.get("checks") or []) if not c.get("ok")][:6]

        # Model presence
        models = home / "models"
        ggufs = list(models.glob("*.gguf")) if models.is_dir() else []
        out["gguf_count"] = len(ggufs)
        if not ggufs:
            out["actions"].append("WARNING: no GGUF under models/")

        out["ok"] = True
        out["summary"] = (
            f"Self-repair: doctor_ok={doc.get('ok')} ggufs={len(ggufs)} "
            f"actions={len(out['actions'])} issue={issue!r}"
        )
    except Exception as e:
        out["error"] = str(e)
    return out
