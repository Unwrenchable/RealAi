#!/usr/bin/env python3
"""
RealAI Self-Heal — multi-repo discovery → gold index → promote → verify

This is the productized form of the work we did by hand:
  scan messy super-repo → assemble abilities/gold → promote uniques → verify stack

Gated by REALAI_SELF_IMPROVE=true for mutating steps (promote apply).
Read-only scan/assemble/status always available when called from orchestrator
with softer gating: status is open; run_scan/assemble require flag OR explicit allow.

Philosophy:
  - Never bulk-merge 10k files
  - Never scan node_modules/venv
  - Always log actions
  - Prefer promote_queue over blind copy
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_PKG = Path(__file__).resolve().parent
_ROOT = _PKG.parent
_SCAN = _ROOT / "scan_results"
_SCANNERS = _ROOT / "scanners"


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _enabled() -> bool:
    return os.environ.get("REALAI_SELF_IMPROVE", "").lower() in ("1", "true", "yes")


def _require() -> None:
    if not _enabled():
        raise PermissionError("Set REALAI_SELF_IMPROVE=true to enable self-heal mutations")


def _run_py(script: Path, args: Optional[List[str]] = None, timeout: int = 600) -> Dict[str, Any]:
    cmd = [sys.executable, str(script)] + (args or [])
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "REALAI_ROOT": str(_ROOT)},
        )
        return {
            "cmd": cmd,
            "returncode": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-2000:],
            "stderr_tail": (proc.stderr or "")[-1000:],
            "ok": proc.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {"cmd": cmd, "ok": False, "error": "timeout", "timeout": timeout}
    except Exception as e:
        return {"cmd": cmd, "ok": False, "error": str(e)}


def status() -> Dict[str, Any]:
    """Snapshot of self-heal capability + artifact presence."""
    artifacts = {
        "era_map": (_SCAN / "era_map.json").is_file(),
        "gold_index": (_SCAN / "gold_index.json").is_file(),
        "promote_queue": (_SCAN / "promote_queue.json").is_file(),
        "gold_index_md": (_SCAN / "gold_index.md").is_file(),
        "dds3_missing_summary": (_SCAN / "dds3_missing_files_summary.json").is_file(),
        "dds3_deep_gold_summary": (_SCAN / "dds3_deep_gold_map_summary.json").is_file(),
        "dds3_ability_inventory": (_SCAN / "dds3_ability_inventory.json").is_file(),
        "dds3_archive_triage": (_SCAN / "dds3_archive_triage.json").is_file(),
        "ability_catalog": (_SCAN / "ability_catalog.json").is_file(),
        "ability_keywords_learned": (_SCAN / "ability_keywords_learned.json").is_file(),
        "ability_surface_training": (_ROOT / "training" / "data" / "ability_surface.jsonl").is_file(),
        "phase2_report": (_SCAN / "phase2_promote_report.md").is_file(),
        "phase3_report": (_SCAN / "phase3_orchestrator_report.md").is_file(),
        "training_dataset": (_ROOT / "training" / "data" / "realai_finetune_dataset.jsonl").is_file(),
        "agent_manifests": (_ROOT / "training" / "data" / "agent_manifests_for_finetuning.json").is_file(),
        "self_improvement_module": (_PKG / "self_improvement.py").is_file(),
        "ability_catalog_module": (_PKG / "ability_catalog.py").is_file(),
        "assemble_script": (_SCANNERS / "assemble_gold_index.py").is_file(),
        "promote_script": (_SCANNERS / "promote_gold.py").is_file(),
        "dds3_script": (_SCANNERS / "dds3_missing_files.py").is_file(),
        "deep_gold_script": (_SCANNERS / "dds3_deep_gold_map.py").is_file(),
        "desktop_scan_script": (_SCANNERS / "scan_desktop_missing_gold.py").is_file(),
        "desktop_missing_gold_map": (_SCAN / "desktop_missing_gold_map.json").is_file(),
        "local_keyword_gold_map": (_SCAN / "local_keyword_gold_map.json").is_file(),
    }
    queue_len = 0
    promote_n = 0
    if artifacts["promote_queue"]:
        try:
            q = json.loads((_SCAN / "promote_queue.json").read_text(encoding="utf-8"))
            queue_len = len(q.get("queue") or [])
            promote_n = sum(1 for i in (q.get("queue") or []) if i.get("action") == "promote")
        except Exception:
            pass

    coverage = None
    try:
        from realai.ability_catalog import coverage_summary
        coverage = coverage_summary()
    except Exception as e:
        coverage = {"error": str(e)}

    return {
        "service": "realai-self-heal",
        "enabled": _enabled(),
        "env": "REALAI_SELF_IMPROVE",
        "root": str(_ROOT),
        "loop": [
            "1. discover (dds3 / deep-gold / desktop+OneDrive missing-file hunt / ability keywords)",
            "2. learn-keywords + ability catalog (technical rundown coverage)",
            "3. assemble (gold_index + promote_queue)",
            "4. promote curated uniques (never bulk 10k)",
            "5. verify stack (vulkan + orchestrator + ui)",
            "6. self_improve evaluate / ability_surface training samples",
        ],
        "desktop_roots": [
            r"C:\Users\tsmit\OneDrive\Desktop",
            r"C:\Users\tsmit\Desktop",
            r"C:\Users\tsmit\Documents",
            r"C:\Users\tsmit\Downloads",
            r"C:\Users\tsmit\realai-clean",
            r"C:\Users\tsmit\realai",
            r"C:\Users\tsmit\realai_historical_backups",
            r"C:\Users\tsmit\backups",
            r"C:\Users\tsmit\Documents\GitHub\realai",
        ],
        "artifacts": artifacts,
        "promote_queue_items": queue_len,
        "promote_actionable": promote_n,
        "ability_coverage": coverage,
        "abilities": {
            "scan_messy_repo": artifacts["dds3_script"] or artifacts["deep_gold_script"],
            "assemble_gold": artifacts["assemble_script"],
            "promote_gold": artifacts["promote_script"],
            "training_data": artifacts["training_dataset"],
            "self_improvement": artifacts["self_improvement_module"],
            "ability_catalog": artifacts["ability_catalog_module"],
            "keyword_learning": artifacts["ability_keywords_learned"] or artifacts["ability_catalog_module"],
        },
        "generated_at": _utc(),
    }


def run_learn_keywords() -> Dict[str, Any]:
    """Merge rundown + inventory + external roots into learned keywords + catalog."""
    try:
        from realai.ability_catalog import (
            build_catalog,
            emit_training_samples,
            learn_keywords_from_scans,
            save_catalog,
        )
        learned = learn_keywords_from_scans(also_tools_cli=True)
        cat_path = save_catalog(build_catalog())
        train = None
        if _enabled():
            try:
                train = emit_training_samples()
            except Exception as e:
                train = {"ok": False, "error": str(e)}
        return {
            "ok": True,
            "learned": {
                "total_count": learned.get("total_count"),
                "added_count": learned.get("added_count"),
                "added_sample": (learned.get("added_this_cycle") or [])[:30],
                "sources": learned.get("sources"),
            },
            "catalog_path": str(cat_path),
            "training": train,
            "status_after": status(),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def run_discover(mode: str = "operational") -> Dict[str, Any]:
    """Run discovery scanners (scoped). Requires REALAI_SELF_IMPROVE.

    Modes:
      operational — dds3 operational + archive triage
      deep — deep gold map
      desktop — OneDrive Desktop + Desktop + Documents/Downloads + realai-clean hunt
      clean — focused realai-clean + historical backups + GitHub realai (same scanner)
      local — alias of desktop (local keyword / missing-file mission)
      abilities — dds3 abilities inventory (uses learned keywords if present)
      all — operational + desktop + abilities + deep (long)
      learn — keyword/catalog only (fast)
    """
    _require()
    results: Dict[str, Any] = {}
    dds3 = _SCANNERS / "dds3_missing_files.py"
    deep = _SCANNERS / "dds3_deep_gold_map.py"
    desktop = _SCANNERS / "scan_desktop_missing_gold.py"
    local_kw = _SCANNERS / "scan_local_keyword_gold.py"

    # Always refresh keyword catalog before ability-oriented scans
    if mode in ("abilities", "all", "learn", "deep", "desktop", "local", "clean"):
        results["learn_keywords"] = run_learn_keywords()

    if mode in ("operational", "all") and dds3.is_file():
        results["dds3"] = _run_py(dds3, ["--mode", "operational", "--also-archive"], timeout=900)
    if mode in ("desktop", "local", "clean", "all") and desktop.is_file():
        # Primary mission: OneDrive Desktop + realai-clean + user local gold
        results["desktop_missing_gold"] = _run_py(desktop, timeout=1200)
    if mode in ("local", "all") and local_kw.is_file():
        # Broader keyword pass (optional; may be long)
        results["local_keyword_gold"] = _run_py(local_kw, timeout=900)
    if mode in ("abilities", "all") and dds3.is_file():
        results["dds3_abilities"] = _run_py(
            dds3, ["--mode", "abilities", "--include-og", "--progress-every", "300"], timeout=900
        )
        # re-learn after inventory so novel tokens stick
        results["learn_keywords_after"] = run_learn_keywords()
    if mode in ("deep", "all") and deep.is_file():
        results["deep_gold"] = _run_py(deep, ["--progress-every", "500"], timeout=900)
    if mode == "learn":
        # already ran learn_keywords above
        pass
    results["status_after"] = status()
    return {"ok": True, "mode": mode, "results": results}


def run_assemble() -> Dict[str, Any]:
    """Distill existing scan_results into promote_queue. Requires flag."""
    _require()
    script = _SCANNERS / "assemble_gold_index.py"
    if not script.is_file():
        return {"ok": False, "error": "assemble_gold_index.py missing"}
    out = _run_py(script, timeout=120)
    out["status_after"] = status()
    return out


def run_promote(apply: bool = False) -> Dict[str, Any]:
    """Promote from queue. apply=False is dry-run. Apply requires flag."""
    _require()
    script = _SCANNERS / "promote_gold.py"
    if not script.is_file():
        return {"ok": False, "error": "promote_gold.py missing"}
    args = ["--apply"] if apply else []
    out = _run_py(script, args, timeout=300)
    out["apply"] = apply
    out["status_after"] = status()
    return out


def run_full_cycle(apply_promote: bool = False) -> Dict[str, Any]:
    """
    Full self-heal cycle:
      assemble (from existing scans) → optional promote → evaluate training readiness
    Does NOT auto-run multi-hour full inventory unless discover first.
    """
    _require()
    cycle: Dict[str, Any] = {"started": _utc(), "steps": []}

    # Prefer assemble from existing artifacts first (fast)
    step_a = run_assemble()
    cycle["steps"].append({"name": "assemble", "result": step_a})

    step_p = run_promote(apply=apply_promote)
    cycle["steps"].append({"name": "promote", "result": step_p})

    # ability catalog + keyword learning (Phase 5F)
    try:
        learn = run_learn_keywords()
        cov = (learn.get("status_after") or {}).get("ability_coverage") or {}
        cycle["steps"].append({
            "name": "ability_learn",
            "result": learn,
            "coverage_pct": (cov.get("coverage") or {}).get("weighted_pct"),
        })
    except Exception as e:
        cycle["steps"].append({"name": "ability_learn", "error": str(e)})

    # self-improve evaluate if available
    try:
        from realai.self_improvement import PerformanceEvaluator
        scores = PerformanceEvaluator().evaluate(model=None)
        cycle["steps"].append({"name": "self_improve_evaluate", "scores": scores})
    except Exception as e:
        cycle["steps"].append({"name": "self_improve_evaluate", "error": str(e)})

    # finetune plan
    try:
        from realai.training.finetune import build_finetune_plan
        cycle["steps"].append({"name": "training_plan", "plan": build_finetune_plan()})
    except Exception as e:
        cycle["steps"].append({"name": "training_plan", "error": str(e)})

    # verify matrix if present
    verify_script = _SCANNERS / "verify_v3_matrix.py"
    if verify_script.is_file():
        cycle["steps"].append({"name": "verify_matrix", "result": _run_py(verify_script, timeout=300)})

    cycle["finished"] = _utc()
    cycle["status"] = status()
    cycle["ok"] = all(
        s.get("result", {}).get("ok", True) if "result" in s else "error" not in s
        for s in cycle["steps"]
    )
    # persist last cycle + human markdown
    try:
        _SCAN.mkdir(parents=True, exist_ok=True)
        (_SCAN / "self_heal_last_cycle.json").write_text(
            json.dumps(cycle, indent=2, default=str), encoding="utf-8"
        )
        cov = (cycle.get("status") or {}).get("ability_coverage") or {}
        cov_pct = (cov.get("coverage") or {}).get("weighted_pct")
        md = [
            "# Self-heal cycle report",
            "",
            f"Started: `{cycle['started']}`",
            f"Finished: `{cycle['finished']}`",
            f"OK: **{cycle['ok']}**  Apply promote: **{apply_promote}**",
            f"Ability coverage vs technical rundown: **{cov_pct}%**",
            "",
            "## Steps",
            "",
        ]
        for s in cycle["steps"]:
            name = s.get("name")
            if "error" in s:
                md.append(f"- **{name}**: ERROR `{s['error']}`")
            elif "scores" in s:
                md.append(f"- **{name}**: scores `{json.dumps(s['scores'])[:200]}`")
            elif "plan" in s:
                md.append(f"- **{name}**: plan status `{s['plan'].get('status')}`")
            elif "coverage_pct" in s:
                md.append(f"- **{name}**: coverage_pct={s.get('coverage_pct')}")
            else:
                r = s.get("result") or {}
                md.append(f"- **{name}**: ok={r.get('ok')} rc={r.get('returncode')}")
        md.append("")
        md.append("## Next for human")
        md.append("")
        md.append("- Review `scan_results/ability_catalog.json` and `docs/ABILITY_SURFACE.md`")
        md.append("- Review `scan_results/gold_index.md` and `promote_queue.json`")
        md.append("- External roots: `C:\\tools\\realai`, Users realai trees, historical backups, Atomic Fizz")
        md.append("- Run cycle with apply only when promote list is trusted")
        md.append("- Keep Vulkan :8080 + orchestrator :8001 + UI :3000 healthy")
        md.append("")
        (_SCAN / "self_heal_last_cycle.md").write_text("\n".join(md), encoding="utf-8")
    except Exception:
        pass
    return cycle


def abilities_manifest() -> Dict[str, Any]:
    """Machine-readable list of self-heal abilities for the agent/UI."""
    st = status()
    cov = st.get("ability_coverage") or {}
    return {
        "name": "RealAI Self-Heal",
        "version": "1.1-5F",
        "description": (
            "Find abilities and broken paths across multi-era messy repos and external "
            "machine gold (OneDrive Desktop, Documents/Downloads, C:\\tools\\realai, Users trees, "
            "historical backups, Atomic Fizz), learn keywords for deeper scans, assemble a "
            "promote queue, curate gold into authority, and verify the live v3 stack."
        ),
        "requires": "REALAI_SELF_IMPROVE=true for mutations",
        "ability_coverage": cov,
        "endpoints": {
            "GET /v1/self-heal/status": "Artifact + ability coverage snapshot",
            "GET /v1/self-heal/abilities": "This manifest + catalog summary",
            "GET /v1/capabilities": "Full ability catalog coverage vs technical rundown",
            "POST /v1/self-heal/assemble": "Rebuild gold index from scan_results",
            "POST /v1/self-heal/promote": "Dry-run or apply promote_queue {apply:bool}",
            "POST /v1/self-heal/discover": (
                "Discovery modes: operational | desktop | clean | local | deep | abilities | all | learn. "
                "desktop/clean/local scan OneDrive Desktop + realai-clean + Documents/Downloads "
                "for missing core files."
            ),
            "POST /v1/self-heal/learn-keywords": "Merge rundown+inventory+external into learned keywords",
            "POST /v1/self-heal/cycle": "Assemble → promote → learn → evaluate {apply:bool}",
        },
        "safety": [
            "Never scans node_modules/venv as product code",
            "Never bulk-merges Phase-4 10k actions",
            "External roots are gold/search targets only",
            "Promote is curated and hash-safe",
            "Memory snapshots stay in recovered/ only",
        ],
        "status": st,
    }
