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
  - Prefer curated allowlist promote (scripts/curated_promote.py) over dump folders
  - Discover is optional; apply curated is the default success path
  - dds3 is optional / never a multi-day full walk
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


def _probe_routes() -> Dict[str, Any]:
    """Cheap honesty check against local orchestrator (opt-in via REALAI_ROUTE_PROBE)."""
    import urllib.request

    base = os.environ.get("REALAI_ORCH", "http://127.0.0.1:8001")
    out: Dict[str, Any] = {}
    for method, path, body in (
        ("GET", "/v1/agents", None),
        ("GET", "/v1/self-heal/status", None),
        ("GET", "/v1/lora", None),
        ("GET", "/v1/tools", None),
        ("POST", "/v1/tools/execute", b'{"name":"list_agents","arguments":{}}'),
        ("POST", "/v1/self-improve/evaluate", b"{}"),
        ("POST", "/v1/multi-agent/run", b'{"task":"ping","mode":"pipeline","max_tokens":32}'),
    ):
        try:
            req = urllib.request.Request(
                base + path,
                data=body,
                method=method,
                headers={"Content-Type": "application/json"} if body else {},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                out[f"{method} {path}"] = resp.status
        except Exception as e:
            out[f"{method} {path}"] = f"fail:{type(e).__name__}"
    return out


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
        "realai_roots_ingest_script": (_SCANNERS / "ingest_realai_roots.py").is_file(),
        "realai_roots_ingest": (_SCAN / "realai_roots_ingest.json").is_file(),
        "realai_roots_D_json": (_ROOT / "scripts" / "realai_roots_D.json").is_file(),
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
            "1. discover (desktop missing-gold + D: realai_roots ingest + keyword learn; dds3 optional)",
            "2. learn-keywords + ability catalog (technical rundown coverage)",
            "3. assemble (gold_index + promote_queue, includes realai_roots_ingest)",
            "4. promote curated uniques (+ optional promote_gold queue)",
            "5. verify stack (orchestrator routes + vulkan + ui)",
            "6. self_improve evaluate / ability_surface training samples",
        ],
        "desktop_roots": [
            r"C:\Users\tsmit\OneDrive\Desktop",
            r"C:\Users\tsmit\Desktop",
            r"C:\Users\tsmit\Documents",
            r"C:\Users\tsmit\Downloads",
            r"C:\RealAI-clean",
            r"C:\Users\tsmit\realai-clean",
            r"C:\Users\tsmit\realai",
            r"C:\Users\tsmit\realai_historical_backups",
            r"C:\Users\tsmit\backups",
            r"C:\Users\tsmit\Documents\GitHub\realai",
            r"D:\RealAI-archive",
            r"D:\realai_archives",
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
            "keyword_learning": artifacts["ability_keywords_learned"]
            or artifacts["ability_catalog_module"],
        },
        "route_probe": (
            _probe_routes()
            if os.environ.get("REALAI_ROUTE_PROBE", "").lower() in ("1", "true", "yes")
            else None
        ),
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
      operational — D: roots ingest + dds3 operational (optional) + assemble-ready artifacts
      deep — deep gold map (optional; can be heavy)
      desktop — OneDrive Desktop + Desktop + Documents/Downloads + realai-clean hunt
      clean — focused realai-clean + historical backups + GitHub realai (same scanner)
      local — alias of desktop (local keyword / missing-file mission)
      roots — ingest scripts/realai_roots_*.json only (fast; no D: re-walk)
      abilities — dds3 abilities inventory (optional)
      all — operational + desktop + abilities + deep (LONG — avoid unless intentional)
      learn — keyword/catalog only (fast)
    """
    _require()
    results: Dict[str, Any] = {}
    dds3 = _SCANNERS / "dds3_missing_files.py"
    deep = _SCANNERS / "dds3_deep_gold_map.py"
    desktop = _SCANNERS / "scan_desktop_missing_gold.py"
    local_kw = _SCANNERS / "scan_local_keyword_gold.py"
    roots = _SCANNERS / "ingest_realai_roots.py"

    # Always refresh keyword catalog before ability-oriented scans
    if mode in ("abilities", "all", "learn", "deep", "desktop", "local", "clean"):
        results["learn_keywords"] = run_learn_keywords()

    # Wire D:/C root inventory JSON into discover (dedupe → candidates). No disk re-walk.
    if mode in ("operational", "desktop", "local", "clean", "roots", "all") and roots.is_file():
        results["realai_roots_ingest"] = _run_py(roots, timeout=300)

    if mode in ("operational", "all") and dds3.is_file():
        results["dds3"] = _run_py(dds3, ["--mode", "operational", "--also-archive"], timeout=900)
    if mode in ("desktop", "local", "clean", "all") and desktop.is_file():
        results["desktop_missing_gold"] = _run_py(desktop, timeout=1200)
    if mode in ("local", "all") and local_kw.is_file():
        results["local_keyword_gold"] = _run_py(local_kw, timeout=900)
    if mode in ("abilities", "all") and dds3.is_file():
        results["dds3_abilities"] = _run_py(
            dds3, ["--mode", "abilities", "--include-og", "--progress-every", "300"], timeout=900
        )
        results["learn_keywords_after"] = run_learn_keywords()
    if mode in ("deep", "all") and deep.is_file():
        results["deep_gold"] = _run_py(deep, ["--progress-every", "500"], timeout=900)
    if mode == "learn":
        pass

    # After roots ingest (and any other scanners), refresh gold index / promote queue.
    if mode in ("operational", "desktop", "local", "clean", "roots", "all"):
        results["assemble"] = run_assemble()

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


def run_curated_promote(apply: bool = True, force: bool = False) -> Dict[str, Any]:
    """
    Allowlist-only promote into live tree. APPLY by default.

    This is the real promote path — not dry-run dump maps.
    """
    if apply:
        _require()
    script = _ROOT / "scripts" / "curated_promote.py"
    if not script.is_file():
        return {"ok": False, "error": "scripts/curated_promote.py missing"}
    args: List[str] = []
    if not apply:
        args.append("--dry-run")
    if force:
        args.append("--force")
    out = _run_py(script, args, timeout=120)
    out["apply"] = apply
    out["force"] = force
    out["status_after"] = status()
    return out


def run_deep_promote(apply: bool = True) -> Dict[str, Any]:
    """Run deep_promote_scan + deep_promote_wire; verify map/queue/wire log exist."""
    if apply:
        _require()
    out: Dict[str, Any] = {"ok": False, "steps": [], "apply": apply}
    scan = _ROOT / "scripts" / "deep_promote_scan.py"
    wire = _ROOT / "scripts" / "deep_promote_wire.py"
    if not scan.is_file():
        return {"ok": False, "error": "scripts/deep_promote_scan.py missing"}
    out["steps"].append({"name": "deep_promote_scan", "result": _run_py(scan, timeout=1800)})
    if wire.is_file():
        args = [] if apply else ["--dry-run"]
        out["steps"].append(
            {"name": "deep_promote_wire", "result": _run_py(wire, args, timeout=600)}
        )
    arts = {}
    for rel in (
        "scan_results/DEEP_PROMOTE_MAP.md",
        "scan_results/deep_promote_queue.json",
        "scan_results/DEEP_PROMOTE_WIRE_LOG.json",
    ):
        p = _ROOT / rel
        arts[rel] = {"exists": p.is_file(), "bytes": p.stat().st_size if p.is_file() else 0}
    out["artifacts"] = arts
    out["ok"] = all(s["result"].get("ok") for s in out["steps"]) and arts[
        "scan_results/DEEP_PROMOTE_MAP.md"
    ]["exists"]
    out["status_after"] = status()
    return out


def run_promote(apply: bool = True) -> Dict[str, Any]:
    """
    Promote gold into live tree.

    curated allowlist + deep promote scan/wire. Falls back to promote_gold.py
    only if curated script is missing.
    """
    steps: List[Dict[str, Any]] = []
    curated = _ROOT / "scripts" / "curated_promote.py"
    if curated.is_file():
        steps.append({"name": "curated_promote", "result": run_curated_promote(apply=apply)})
    else:
        _require()
        script = _SCANNERS / "promote_gold.py"
        if not script.is_file():
            return {
                "ok": False,
                "error": "No promote worker: need scripts/curated_promote.py or scanners/promote_gold.py",
            }
        args = ["--apply"] if apply else []
        steps.append(
            {"name": "promote_gold", "result": _run_py(script, args, timeout=300)}
        )

    if (_ROOT / "scripts" / "deep_promote_scan.py").is_file():
        steps.append({"name": "deep_promote", "result": run_deep_promote(apply=apply)})

    out: Dict[str, Any] = {
        "ok": all(bool((s.get("result") or {}).get("ok")) for s in steps),
        "apply": apply,
        "steps": steps,
        "status_after": status(),
    }
    return out


def run_full_cycle(apply_promote: bool = True) -> Dict[str, Any]:
    """
    Full self-heal cycle (apply curated promote by default):
      assemble → curated promote → promote_gold queue → ability learn → evaluate
    Does NOT dump recovered/* folders. Does NOT run multi-day dds3.
    """
    _require()
    cycle: Dict[str, Any] = {"started": _utc(), "steps": []}

    # Optional assemble only if scanner present
    if (_SCANNERS / "assemble_gold_index.py").is_file():
        step_a = run_assemble()
        cycle["steps"].append({"name": "assemble", "result": step_a})
    else:
        cycle["steps"].append(
            {
                "name": "assemble",
                "result": {
                    "ok": True,
                    "skipped": True,
                    "reason": "no assemble_gold_index.py — using curated only",
                },
            }
        )

    step_p = run_promote(apply=apply_promote)
    cycle["steps"].append({"name": "promote", "result": step_p})

    # Optional: apply promote_queue via promote_gold (ROOT must be RealAI-clean)
    pg = _SCANNERS / "promote_gold.py"
    if pg.is_file() and apply_promote:
        cycle["steps"].append(
            {
                "name": "promote_gold_queue",
                "result": _run_py(pg, ["--apply"], timeout=300),
            }
        )

    # ability catalog + keyword learning
    try:
        learn = run_learn_keywords()
        cov = (learn.get("status_after") or {}).get("ability_coverage") or {}
        cycle["steps"].append(
            {
                "name": "ability_learn",
                "result": learn,
                "coverage_pct": (cov.get("coverage") or {}).get("weighted_pct"),
            }
        )
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
        cycle["steps"].append(
            {"name": "verify_matrix", "result": _run_py(verify_script, timeout=300)}
        )

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
        md.append(
            "- External roots: `C:\\tools\\realai`, Users realai trees, historical backups, Atomic Fizz"
        )
        md.append("- Run cycle with apply only when promote list is trusted")
        md.append("- Keep Vulkan :8080 + orchestrator :8001 + UI :3000 healthy")
        md.append("- Do not run full dds3 multi-day scans")
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
        "version": "1.2-route-probe",
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
                "Discovery modes: operational | desktop | clean | local | roots | deep | abilities | all | learn. "
                "roots/operational ingest scripts/realai_roots_*.json (no D: re-walk) then assemble gold index. "
                "Prefer roots/desktop/learn. Avoid all/deep/dds3 full walks."
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
            "dds3 full walks are optional and not part of the default cycle",
        ],
        "status": st,
    }