#!/usr/bin/env python3
"""
live_gap_agent.py — bounded RealAI live-surface gap finder / optional fixer.

Default = dry-run (report only).
Never walks temp_repos / recovered dumps / venv / node_modules.
Never runs dds3.

Phases:
  1. Inventory product trees (core, modules, plugins, agent_tools, realai)
  2. Compare to live tools_catalog + ability_catalog + plugin registry
  3. Classify gaps
  4. Optionally apply SAFE fixes only:
       - ability status PARTIAL→LIVE when route probe already 200
       - append real plugin manifests into registry.json
       - record recommendations for human / next cycle

Usage:
  python scripts/live_gap_agent.py
  python scripts/live_gap_agent.py --dry-run
  python scripts/live_gap_agent.py --apply --only catalog-status
  python scripts/live_gap_agent.py --apply --only plugin-registry,catalog-status
  python scripts/live_gap_agent.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SCAN = ROOT / "scan_results"
OUT_JSON = SCAN / "live_gaps.json"
OUT_MD = SCAN / "live_gaps.md"

PRODUCT_ROOTS = ("core", "modules", "plugins", "agent_tools", "realai")
IGNORE_DIR_NAMES = {
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    ".backup",
    "site-packages",
    "Lib",
    "temp_repos",
    "recovered",
    "RealAI_Recovery_SAFE",
    "realai_historical_backups",
    "archive",
    "models",
    "dist",
    "build",
}

# Abilities we already verified via POST/GET against orchestrator
VERIFIED_ROUTE_ABILITIES = {
    "code_execution": "POST /v1/tools/execute",
    "multi_agent": "POST /v1/multi-agent/run",
    "self_reflection": "POST /v1/self-improve/evaluate",
    "task_automation": "GET /v1/self-heal/status",
    "observability_self_improve": "GET /v1/self-heal/status",
    "training_pipeline": "GET /v1/training/plan",
    "lora_adapters": "GET /v1/lora",
}


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _should_skip(path: Path) -> bool:
    return any(part in IGNORE_DIR_NAMES for part in path.parts)


def _iter_py(root: Path, max_files: int = 5000) -> List[Path]:
    if not root.is_dir():
        return []
    out: List[Path] = []
    for p in root.rglob("*.py"):
        if _should_skip(p):
            continue
        # skip flattened backup junk names
        if p.name.startswith("C__realai") or "backup_clean_backup" in p.name:
            continue
        out.append(p)
        if len(out) >= max_files:
            break
    return out


def _probe_routes() -> Dict[str, Any]:
    base = os.environ.get("REALAI_ORCH", "http://127.0.0.1:8001")
    out: Dict[str, Any] = {}
    checks = [
        ("GET", "/v1/agents", None),
        ("GET", "/v1/tools", None),
        ("GET", "/v1/self-heal/status", None),
        ("GET", "/v1/lora", None),
        ("GET", "/v1/training/plan", None),
        ("POST", "/v1/tools/execute", b'{"name":"list_agents","arguments":{}}'),
        ("POST", "/v1/self-improve/evaluate", b"{}"),
        ("POST", "/v1/multi-agent/run", b'{"task":"ping","mode":"pipeline","max_tokens":16}'),
    ]
    for method, path, body in checks:
        key = f"{method} {path}"
        try:
            req = urllib.request.Request(
                base + path,
                data=body,
                method=method,
                headers={"Content-Type": "application/json"} if body else {},
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                out[key] = resp.status
        except Exception as e:
            out[key] = f"fail:{type(e).__name__}"
    return out


def inventory_product() -> Dict[str, Any]:
    inv: Dict[str, Any] = {"roots": {}, "core_packages": {}, "plugin_dirs": [], "modules": []}
    for name in PRODUCT_ROOTS:
        root = ROOT / name
        files = _iter_py(root) if root.is_dir() else []
        inv["roots"][name] = {
            "exists": root.is_dir(),
            "py_count": len(files),
            "sample": [str(p.relative_to(ROOT)) for p in files[:15]],
        }

    for d in (
        "agents",
        "tools",
        "voice",
        "web3",
        "inference",
        "memory",
        "orchestration",
        "training",
    ):
        p = ROOT / "core" / d
        inv["core_packages"][d] = {
            "exists": p.is_dir(),
            "py_count": len(list(p.glob("**/*.py"))) if p.is_dir() else 0,
        }

    for base in (ROOT / "plugins", ROOT / "realai" / "plugins"):
        if not base.is_dir():
            continue
        for child in base.iterdir():
            if child.is_dir() and child.name not in ("__pycache__",):
                if child.name.startswith("C__") or "backup" in child.name.lower():
                    continue
                inv["plugin_dirs"].append(str(child.relative_to(ROOT)))

    organs = ROOT / "modules" / "organs"
    if organs.is_dir():
        inv["modules"] = [
            str(p.relative_to(ROOT))
            for p in organs.rglob("*.py")
            if not _should_skip(p)
        ][:40]
    return inv


def live_tools() -> List[str]:
    try:
        from realai.v3_runtime_bridge import tools_catalog

        names = []
        for t in tools_catalog():
            n = (t.get("function") or {}).get("name")
            if n:
                names.append(n)
        return sorted(set(names))
    except Exception as e:
        return [f"ERROR:{e}"]


def ability_entries() -> List[Dict[str, Any]]:
    try:
        from realai.ability_catalog import build_catalog

        cat = build_catalog()
        return list(cat.get("abilities") or [])
    except Exception:
        # fallback generated file
        p = SCAN / "ability_catalog.json"
        if p.is_file():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return list(data.get("abilities") or [])
            except Exception:
                pass
        return []


def load_plugin_registry() -> List[Dict[str, Any]]:
    p = ROOT / "realai" / "plugins" / "registry.json"
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def find_plugin_manifests() -> List[Dict[str, Any]]:
    """Real plugin manifests (not recovery JSON dumps)."""
    found: List[Dict[str, Any]] = []
    patterns = ("plugin_manifest.json", "manifest.json")
    search_roots = [ROOT / "plugins", ROOT / "realai" / "plugins"]
    for base in search_roots:
        if not base.is_dir():
            continue
        for pat in patterns:
            for p in base.rglob(pat):
                if _should_skip(p):
                    continue
                if "backup" in str(p).lower() or "C__" in p.name:
                    continue
                try:
                    data = json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    continue
                name = data.get("name") or data.get("id") or p.parent.name
                if not name or name in (
                    "ability_catalog",
                    "ability_keywords_learned",
                    "dds3_ability_inventory",
                ):
                    continue
                found.append(
                    {
                        "name": name,
                        "path": str(p.relative_to(ROOT)),
                        "version": data.get("version") or "unknown",
                        "capabilities": data.get("capabilities") or data.get("abilities") or [],
                        "raw_keys": list(data.keys())[:20],
                    }
                )
    # also rackup coach dirs without formal manifest
    for coach in (ROOT / "plugins" / "rackup_coach", ROOT / "plugins" / "rackup-coach"):
        if coach.is_dir():
            found.append(
                {
                    "name": "rackup_coach",
                    "path": str(coach.relative_to(ROOT)),
                    "version": "in-tree",
                    "capabilities": ["league", "rating", "coach"],
                    "raw_keys": [],
                }
            )
    # dedupe by name
    by: Dict[str, Dict[str, Any]] = {}
    for f in found:
        by[str(f["name"])] = f
    return list(by.values())


def classify_gaps(
    inv: Dict[str, Any],
    tools: List[str],
    abilities: List[Dict[str, Any]],
    registry: List[Dict[str, Any]],
    manifests: List[Dict[str, Any]],
    routes: Dict[str, Any],
) -> List[Dict[str, Any]]:
    gaps: List[Dict[str, Any]] = []
    toolset = set(tools)

    # core tools expected after bridge
    for expected in ("core.web_search", "core.code_exec", "core.file_tool"):
        if expected not in toolset and not any(t.startswith("ERROR") for t in tools):
            gaps.append(
                {
                    "type": "missing_core_tool",
                    "id": expected,
                    "severity": "high",
                    "action": "ensure v3_runtime_bridge core bridge is loaded / restart orchestrator",
                    "auto": False,
                }
            )

    # abilities PARTIAL/GOLD with verified routes → catalog-status candidate
    for a in abilities:
        aid = a.get("id")
        st = a.get("status")
        if not aid or st == "LIVE":
            continue
        if aid in VERIFIED_ROUTE_ABILITIES:
            route = VERIFIED_ROUTE_ABILITIES[aid]
            # map to probe key roughly
            probe_ok = False
            for k, v in routes.items():
                if isinstance(v, int) and v == 200:
                    # loose match
                    path = k.split(" ", 1)[-1]
                    if path in route or any(
                        p in route for p in (path,)
                    ):
                        probe_ok = True
                        break
                if aid == "code_execution" and routes.get("POST /v1/tools/execute") == 200:
                    probe_ok = True
                if aid == "multi_agent" and routes.get("POST /v1/multi-agent/run") == 200:
                    probe_ok = True
                if aid == "self_reflection" and routes.get("POST /v1/self-improve/evaluate") == 200:
                    probe_ok = True
                if aid in ("task_automation", "observability_self_improve") and routes.get(
                    "GET /v1/self-heal/status"
                ) == 200:
                    probe_ok = True
                if aid == "training_pipeline" and routes.get("GET /v1/training/plan") == 200:
                    probe_ok = True
                if aid == "lora_adapters" and routes.get("GET /v1/lora") == 200:
                    probe_ok = True
            gaps.append(
                {
                    "type": "catalog_status",
                    "id": aid,
                    "status": st,
                    "live_path": a.get("live_path") or route,
                    "probe_ok": probe_ok,
                    "severity": "medium" if probe_ok else "low",
                    "action": "PARTIAL/GOLD → LIVE in ability_catalog.py"
                    if probe_ok
                    else "verify route then promote",
                    "auto": bool(probe_ok),
                }
            )

    # plugin manifests not in registry
    reg_names = {str(x.get("name")) for x in registry}
    for m in manifests:
        if m["name"] not in reg_names:
            gaps.append(
                {
                    "type": "plugin_registry",
                    "id": m["name"],
                    "path": m.get("path"),
                    "version": m.get("version"),
                    "capabilities": m.get("capabilities"),
                    "severity": "medium",
                    "action": "append to realai/plugins/registry.json",
                    "auto": True,
                    "manifest": m,
                }
            )

    # core packages present but no core.* tools beyond tools package
    if inv.get("core_packages", {}).get("web3", {}).get("exists") and not any(
        t.startswith("core.") and "web3" in t for t in toolset
    ):
        gaps.append(
            {
                "type": "unwired_core_package",
                "id": "core.web3",
                "severity": "low",
                "action": "optional: register Web3Tool in bridge (permission-gated)",
                "auto": False,
            }
        )
    if inv.get("core_packages", {}).get("voice", {}).get("exists"):
        gaps.append(
            {
                "type": "unwired_core_package",
                "id": "core.voice",
                "severity": "low",
                "action": "wire after audio routes exist",
                "auto": False,
            }
        )
    if inv.get("core_packages", {}).get("agents", {}).get("exists"):
        gaps.append(
            {
                "type": "unwired_core_package",
                "id": "core.agents",
                "severity": "medium",
                "action": "optional alternate backend for run_multi_agent",
                "auto": False,
            }
        )

    # registry polluted with scan artifacts
    for junk in ("ability_catalog", "ability_keywords_learned", "dds3_ability_inventory"):
        if junk in reg_names:
            gaps.append(
                {
                    "type": "registry_noise",
                    "id": junk,
                    "severity": "low",
                    "action": "remove scan JSON from plugin registry (not a plugin)",
                    "auto": True,
                }
            )

    return gaps


def apply_catalog_status(gaps: List[Dict[str, Any]], apply: bool) -> List[Dict[str, Any]]:
    """Flip verified PARTIAL abilities to LIVE in ability_catalog.py source."""
    results = []
    catalog = ROOT / "realai" / "ability_catalog.py"
    if not catalog.is_file():
        return [{"ok": False, "error": "ability_catalog.py missing"}]
    text = catalog.read_text(encoding="utf-8")
    original = text
    for g in gaps:
        if g.get("type") != "catalog_status" or not g.get("auto") or not g.get("probe_ok"):
            continue
        aid = g["id"]
        if g.get("status") == "LIVE":
            results.append({"id": aid, "ok": True, "skipped": True, "reason": "already LIVE"})
            continue
        pattern = rf'("id":\s*"{re.escape(aid)}".{{0,400}}?"status":\s*)"(PARTIAL|GOLD|CODE|SOFT)"'
        text2, n = re.subn(pattern, r'\1"LIVE"', text, count=1, flags=re.S)
        if n:
            text = text2
            results.append({"id": aid, "ok": True, "changed": True, "applied": apply})
        else:
            results.append({"id": aid, "ok": False, "error": "pattern_not_found"})
    if apply and text != original:
        catalog.write_text(text, encoding="utf-8")
        try:
            from realai.ability_catalog import build_catalog, save_catalog

            save_catalog(build_catalog())
        except Exception as e:
            results.append({"ok": False, "error": f"rebuild_catalog:{e}"})
    return results


def apply_plugin_registry(gaps: List[Dict[str, Any]], apply: bool) -> List[Dict[str, Any]]:
    results = []
    path = ROOT / "realai" / "plugins" / "registry.json"
    reg = load_plugin_registry()
    names = {str(x.get("name")) for x in reg}
    changed = False

    # remove noise
    for g in gaps:
        if g.get("type") == "registry_noise" and g.get("auto"):
            before = len(reg)
            reg = [x for x in reg if str(x.get("name")) != g["id"]]
            if len(reg) != before:
                changed = True
                results.append({"id": g["id"], "ok": True, "removed": True, "applied": apply})
            names = {str(x.get("name")) for x in reg}

    # append manifests
    for g in gaps:
        if g.get("type") != "plugin_registry" or not g.get("auto"):
            continue
        mid = g["id"]
        if mid in names:
            results.append({"id": mid, "ok": True, "skipped": True})
            continue
        entry = {
            "source": g.get("path") or "",
            "name": mid,
            "version": g.get("version") or "unknown",
            "capabilities": g.get("capabilities") or [],
        }
        reg.append(entry)
        names.add(mid)
        changed = True
        results.append({"id": mid, "ok": True, "added": True, "applied": apply})

    if apply and changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(reg, indent=2), encoding="utf-8")
    return results


def write_reports(report: Dict[str, Any]) -> None:
    SCAN.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    lines = [
        "# Live gaps report",
        "",
        f"Generated: `{report.get('generated_at')}`",
        f"Mode: **{report.get('mode')}**",
        f"Live tools: **{report.get('live_tool_count')}**",
        f"Gaps: **{len(report.get('gaps') or [])}**",
        "",
        "## Route probe",
        "",
    ]
    for k, v in (report.get("routes") or {}).items():
        lines.append(f"- `{k}`: `{v}`")
    lines.extend(["", "## Gaps", ""])
    for g in report.get("gaps") or []:
        lines.append(
            f"- **{g.get('type')}** `{g.get('id')}` — {g.get('action')} "
            f"(severity={g.get('severity')}, auto={g.get('auto')})"
        )
    if report.get("apply_results"):
        lines.extend(["", "## Apply results", ""])
        lines.append("```json")
        lines.append(json.dumps(report["apply_results"], indent=2, default=str)[:4000])
        lines.append("```")
    lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Bounded RealAI live gap agent")
    ap.add_argument("--apply", action="store_true", help="Apply safe auto fixes")
    ap.add_argument(
        "--only",
        default="catalog-status,plugin-registry",
        help="Comma list: catalog-status,plugin-registry",
    )
    ap.add_argument("--json", action="store_true", help="Print full JSON report")
    ap.add_argument("--no-probe", action="store_true", help="Skip HTTP route probe")
    args = ap.parse_args()
    only = {x.strip() for x in (args.only or "").split(",") if x.strip()}

    if args.apply and os.environ.get("REALAI_SELF_IMPROVE", "").lower() not in (
        "1",
        "true",
        "yes",
    ):
        print(
            "[live_gap] REFUSING --apply without REALAI_SELF_IMPROVE=true",
            file=sys.stderr,
        )
        return 2

    print("[live_gap] inventory product trees...")
    inv = inventory_product()
    print("[live_gap] live tools...")
    tools = live_tools()
    print("[live_gap] abilities...")
    abilities = ability_entries()
    print("[live_gap] plugin registry + manifests...")
    registry = load_plugin_registry()
    manifests = find_plugin_manifests()
    routes: Dict[str, Any] = {}
    if not args.no_probe:
        print("[live_gap] route probe...")
        routes = _probe_routes()

    gaps = classify_gaps(inv, tools, abilities, registry, manifests, routes)

    apply_results: Dict[str, Any] = {}
    if args.apply:
        if "catalog-status" in only:
            print("[live_gap] apply catalog-status...")
            apply_results["catalog_status"] = apply_catalog_status(gaps, apply=True)
        if "plugin-registry" in only:
            print("[live_gap] apply plugin-registry...")
            apply_results["plugin_registry"] = apply_plugin_registry(gaps, apply=True)
    else:
        # still compute what would happen
        if "catalog-status" in only:
            apply_results["catalog_status_preview"] = apply_catalog_status(gaps, apply=False)
        if "plugin-registry" in only:
            apply_results["plugin_registry_preview"] = apply_plugin_registry(gaps, apply=False)

    report = {
        "generated_at": _utc(),
        "mode": "apply" if args.apply else "dry-run",
        "root": str(ROOT),
        "live_tool_count": len([t for t in tools if not str(t).startswith("ERROR")]),
        "live_tools": tools,
        "inventory": inv,
        "routes": routes,
        "registry_names": [x.get("name") for x in registry],
        "manifests": manifests,
        "gaps": gaps,
        "apply_results": apply_results,
        "outputs": {"json": str(OUT_JSON), "md": str(OUT_MD)},
    }
    write_reports(report)

    # summary
    by_type: Dict[str, int] = {}
    for g in gaps:
        by_type[g["type"]] = by_type.get(g["type"], 0) + 1
    print(f"[live_gap] tools={report['live_tool_count']} gaps={len(gaps)} by_type={by_type}")
    print(f"[live_gap] wrote {OUT_JSON}")
    print(f"[live_gap] wrote {OUT_MD}")
    if args.json:
        print(json.dumps(report, indent=2, default=str)[:12000])
    else:
        for g in gaps[:25]:
            print(
                f"  - {g.get('type'):22} {g.get('id'):28} auto={g.get('auto')}  {g.get('action')}"
            )
        if len(gaps) > 25:
            print(f"  ... {len(gaps) - 25} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())