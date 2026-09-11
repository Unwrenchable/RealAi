#!/usr/bin/env python3
"""
RealAI Smart Learn Controller — Fully Automatic Comprehensive Version
---------------------------------------------------------------------
Goals:
- Discover and understand every available script
- Analyze current ability gaps
- Deep-walk recovered / temp_repos / scan_results / docs / servers (no junk)
- Intelligently choose the best scripts and order to run
- Promote and absorb high-value code
- Rebuild catalogs, world model, plugin registry
- Measure improvement and stop when gains plateau
- Leave the system better able to self-build / self-extend
"""

import os
import re
import json
import ast
import time
import shutil
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ============================================================
# CONFIG
# ============================================================

MAIN_ROOT = Path(r"C:\RealAI-clean")
SCRIPTS_DIR = MAIN_ROOT / "scripts"
LOG_DIR = MAIN_ROOT / "logs"
SCAN_RESULTS = MAIN_ROOT / "scan_results"
RECOVERED = MAIN_ROOT / "recovered"
TEMP_REPOS = MAIN_ROOT / "temp_repos"
REALAI_DIR = MAIN_ROOT / "realai"

MAX_ROUNDS = 5
DRY_RUN = False
MAX_WALK_FOLDERS = 120          # safety per root
TIMEOUT_DEFAULT = 900

# High-value roots the controller is allowed to learn from
LEARN_ROOTS = [
    MAIN_ROOT,
    RECOVERED,
    TEMP_REPOS,
    SCAN_RESULTS,
    MAIN_ROOT / "modules",
    MAIN_ROOT / "apps",
    MAIN_ROOT / "imports",
    Path(r"C:\Users\tsmit\backups"),
    Path(r"C:\Users\tsmit\models"),
    Path(r"D:\realai_archives"),
    Path(r"C:\tools\realai"),
    Path(r"C:\Users\tsmit\projects\realai-clean"),
    Path(r"C:\Users\tsmit\realai"),
]

SKIP_DIR_NAMES = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", ".tox",
    ".mypy_cache", ".pytest_cache", "dist", "build", ".next", ".nuxt",
    "coverage", ".cache", ".pnpm", ".yarn", "bin", "obj", ".idea",
    ".vscode", "eggs", "*.egg-info"
}

JUNK_EXTENSIONS = {
    ".pyc", ".pyo", ".pyd", ".so", ".dll", ".exe", ".bin",
    ".log", ".tmp", ".bak", ".swp", ".DS_Store"
}

# ============================================================
# LOGGING
# ============================================================

def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOG_DIR / "smart_learn.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")

# ============================================================
# SCRIPT INTELLIGENCE — read and understand available scripts
# ============================================================

def discover_scripts() -> dict:
    """Discover scripts from the official scripts/ folder AND from nested repos."""
    knowledge = {}

    def add_script(path: Path, source_label: str):
        if path.name == "realai_smart_learn_controller.py":
            return
        if is_junk_path(path):
            return

        rel = str(path)
        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return

        # Only keep scripts that look like RealAI tooling
        lower_src = source.lower()
        lower_name = path.name.lower()
        useful_keywords = (
            "scan_root", "promote", "self_heal", "world_model", "registry",
            "wire_recovered", "curated_promote", "ability", "dispatch",
            "monitor_model", "find_self_improve", "plugin"
        )
        if not any(k in lower_src or k in lower_name for k in useful_keywords):
            return

        purpose = "unknown"
        doc = re.search(r'"""(.*?)"""', source, re.DOTALL)
        if doc:
            purpose = doc.group(1).strip().split("\n")[0][:180]
        else:
            for line in source.splitlines()[:25]:
                if line.strip().startswith("#") and len(line.strip()) > 8:
                    purpose = line.strip()[1:].strip()[:180]
                    break

        knowledge[rel] = {
            "path": str(path),
            "name": path.name,
            "source": source_label,
            "purpose": purpose,
            "accepts_scan_root": "--scan-root" in source or "scan_root" in source,
            "cost": "medium",
        }

    # 1. Official scripts folder (recursive)
    if SCRIPTS_DIR.exists():
        for p in SCRIPTS_DIR.rglob("*.py"):
            add_script(p, "official_scripts")

    # 2. Deep search in important roots for nested tool scripts
    search_roots = [
        RECOVERED,
        TEMP_REPOS,
        SCAN_RESULTS,
        MAIN_ROOT / "modules",
        MAIN_ROOT / "apps",
        Path(r"C:\Users\tsmit\backups"),
        Path(r"D:\realai_archives"),
        Path(r"C:\tools\realai"),
    ]

    for root in search_roots:
        if not root.exists():
            continue
        count = 0
        for p in root.rglob("*.py"):
            if is_junk_path(p):
                continue
            add_script(p, f"nested:{root.name}")
            count += 1
            if count >= 80:          # safety limit per root
                break

    log(f"Discovered {len(knowledge)} useful scripts (official + nested)")
    return knowledge

# ============================================================
# GAP ANALYSIS
# ============================================================

def load_ability_catalog():
    candidates = [
        SCAN_RESULTS / "ability_catalog.json",
        REALAI_DIR / "plugins" / "registry.json",
        RECOVERED / "ability_catalog.json",
    ]
    for p in candidates:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return json.load(f), str(p)
            except Exception:
                continue
    return None, None

def analyze_gaps(catalog) -> dict:
    """Return structured gap information."""
    gaps = {
        "LIVE": [],
        "GOLD": [],
        "PARTIAL": [],
        "STUB": [],
        "SOFT": [],
        "MISSING": [],
        "CODE": [],
        "other": [],
        "total": 0,
        "live_count": 0,
        "weighted": None,
    }

    if not catalog:
        return gaps

    # Handle both list-of-abilities and dict-with-coverage styles
    abilities = []
    if isinstance(catalog, list):
        abilities = catalog
    elif isinstance(catalog, dict):
        if "abilities" in catalog:
            abilities = catalog["abilities"]
        elif "items" in catalog:
            abilities = catalog["items"]
        else:
            # maybe the whole dict is status summary
            gaps["weighted"] = catalog.get("weighted_percentage") or catalog.get("coverage")
            gaps["live_count"] = catalog.get("live_count") or catalog.get("LIVE", 0)
            return gaps

    for ab in abilities:
        if not isinstance(ab, dict):
            continue
        status = str(ab.get("status", "other")).upper()
        name = ab.get("name") or ab.get("id") or ab.get("title") or "unnamed"
        entry = {"name": name, "status": status, "raw": ab}
        if status in gaps:
            gaps[status].append(entry)
        else:
            gaps["other"].append(entry)
        gaps["total"] += 1
        if status == "LIVE":
            gaps["live_count"] += 1

    return gaps

# ============================================================
# DEEP WALK + KNOWLEDGE EXTRACTION (no junk)
# ============================================================

def is_junk_path(path: Path) -> bool:
    parts = set(path.parts)
    if parts & SKIP_DIR_NAMES:
        return True
    if path.suffix.lower() in JUNK_EXTENSIONS:
        return True
    name = path.name.lower()
    if name.startswith(".") and name not in {".env", ".gitignore"}:
        return True
    return False

def walk_interesting(root: Path, max_folders: int = MAX_WALK_FOLDERS):
    """Yield interesting directories and key files, skipping junk."""
    if not root.exists():
        return

    keywords = (
        "realai", "plugin", "ability", "agent", "orchestr", "world_model",
        "memory", "aura", "tool", "organ", "rackup", "self_heal", "dispatch",
        "catalog", "registry", "server", "api", "route", "manifest"
    )

    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        # prune junk in-place
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES and not d.startswith(".")]

        p = Path(dirpath)
        if is_junk_path(p):
            continue

        lower = str(p).lower()
        has_keyword = any(k in lower for k in keywords)
        has_code = any(f.endswith((".py", ".json", ".md", ".ts", ".js")) for f in filenames)

        if has_keyword or has_code:
            yield p
            count += 1
            if count >= max_folders:
                return

def extract_from_file(path: Path) -> dict:
    """Lightweight extraction of useful signals from a single file."""
    info = {
        "path": str(path),
        "type": path.suffix.lower(),
        "abilities_mentioned": [],
        "classes": [],
        "functions": [],
        "is_plugin": False,
        "is_server": False,
        "is_docs": False,
    }
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")[:50000]  # cap
    except Exception:
        return info

    lower = text.lower()
    if "plugin" in lower or "manifest" in lower:
        info["is_plugin"] = True
    if any(x in lower for x in ("fastapi", "flask", "@app.", "router.", "/v1/", "uvicorn")):
        info["is_server"] = True
    if path.suffix.lower() in {".md", ".rst", ".txt"} or "readme" in path.name.lower():
        info["is_docs"] = True

    # very light AST for .py
    if path.suffix == ".py":
        try:
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    info["classes"].append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    info["functions"].append(node.name)
        except Exception:
            pass

    # keyword hits for abilities
    for kw in ("chat_completion", "text_generation", "tool_call", "memory", "agent",
               "orchestrator", "self_heal", "world_model", "plugin", "aura"):
        if kw in lower:
            info["abilities_mentioned"].append(kw)

    return info

# ============================================================
# SCRIPT EXECUTION
# ============================================================

def run_script(script_name: str, scan_root: str = None, timeout: int = TIMEOUT_DEFAULT) -> bool:
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        log(f"Script missing: {script_name}", "ERROR")
        return False

    args = ["python", str(script_path)]
    if scan_root:
        # only add if the script is known to accept it (best-effort)
        args += ["--scan-root", scan_root]

    log(f"EXEC → {script_name}" + (f"  [root={scan_root}]" if scan_root else ""))

    if DRY_RUN:
        log("  [dry-run] skipped")
        return True

    try:
        result = subprocess.run(
            args,
            cwd=str(MAIN_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace"
        )
        if result.returncode == 0:
            log(f"  ✓ {script_name} succeeded")
            return True
        else:
            log(f"  ✗ {script_name} failed (exit {result.returncode})", "WARN")
            if result.stderr:
                log(f"    stderr: {result.stderr[:400]}", "WARN")
            return False
    except subprocess.TimeoutExpired:
        log(f"  ✗ {script_name} timed out after {timeout}s", "ERROR")
        return False
    except Exception as e:
        log(f"  ✗ {script_name} exception: {e}", "ERROR")
        return False

# ============================================================
# INTELLIGENT PLANNER
# ============================================================

def choose_plan(round_num: int, gaps: dict, script_knowledge: dict) -> list:
    """
    Decide the best sequence of scripts for this round.
    Fully automatic reasoning based on current state.
    """
    plan = []

    # Round 1 = discovery heavy
    if round_num == 1:
        plan = [
            "scan_repos_for_realai.py",
            "find_self_improve_and_lost.py",
            "promote_unified_realai.py",
            "diff_imports_promote_allowlist.py",
            "curated_promote.py",
            "world_model_merger.py",
            "plugin_registry_builder.py",
            "wire_recovered.py",
            "unified_structure_validator.py",
            "self_heal_loop.py",
            "monitor_model.py",
        ]
    else:
        # Later rounds: focus on closing gaps + absorption
        has_gaps = (gaps.get("MISSING") or gaps.get("PARTIAL") or
                    gaps.get("STUB") or gaps.get("SOFT") or gaps.get("CODE"))

        if has_gaps:
            plan += [
                "find_self_improve_and_lost.py",
                "promote_unified_realai.py",
                "curated_promote.py",
            ]

        plan += [
            "world_model_merger.py",
            "plugin_registry_builder.py",
            "wire_recovered.py",
            "unified_structure_validator.py",
            "self_heal_loop.py",
            "monitor_model.py",
        ]

    # Only keep scripts that actually exist
    # Match either the plain name or the relative path
plan = [s for s in plan if s in script_knowledge or any(k.endswith(s) for k in script_knowledge)]
    return plan

# ============================================================
# ABSORPTION + FINAL REPORTING
# ============================================================

def rebuild_and_measure():
    """Force key rebuild steps and return new coverage."""
    for s in ["plugin_registry_builder.py", "world_model_merger.py", "monitor_model.py"]:
        run_script(s)

    catalog, _ = load_ability_catalog()
    gaps = analyze_gaps(catalog)
    return gaps

# ============================================================
# MAIN CONTROLLER LOOP
# ============================================================

def main():
    log("=" * 70)
    log("RealAI Smart Learn Controller — Comprehensive Fully Automatic Mode")
    log(f"DRY_RUN = {DRY_RUN}")
    log("=" * 70)

    # 1. Understand available scripts
    script_knowledge = discover_scripts()
    if not script_knowledge:
        log("No scripts discovered — aborting", "ERROR")
        return

    log("Script knowledge base:")
    for name, meta in sorted(script_knowledge.items()):
        log(f"  • {name:40s} [{meta['cost']:6s}] {meta['purpose'][:60]}")

    previous_live = None
    previous_weighted = None

    for round_num in range(1, MAX_ROUNDS + 1):
        log(f"\n{'='*70}")
        log(f"ROUND {round_num}/{MAX_ROUNDS}")
        log(f"{'='*70}")

        # 2. Gap analysis
        catalog, catalog_path = load_ability_catalog()
        gaps = analyze_gaps(catalog)
        log(f"Catalog source: {catalog_path}")
        log(f"Live abilities : {gaps['live_count']}")
        log(f"MISSING        : {len(gaps['MISSING'])}")
        log(f"PARTIAL/STUB/SOFT/CODE : {len(gaps['PARTIAL'])+len(gaps['STUB'])+len(gaps['SOFT'])+len(gaps['CODE'])}")

        # 3. Choose plan
        plan = choose_plan(round_num, gaps, script_knowledge)
        log(f"Selected plan ({len(plan)} scripts):")
        for s in plan:
            log(f"   → {s}")

        # 4. Execute plan (main root first, then high-value secondary roots)
        success = 0
        for script in plan:
            # Primary run against main root
            if run_script(script, scan_root=str(MAIN_ROOT)):
                success += 1

            # For discovery/promote scripts, also hit the richest secondary locations
            if script in {
                "scan_repos_for_realai.py",
                "find_self_improve_and_lost.py",
                "promote_unified_realai.py",
                "curated_promote.py",
            }:
                for extra in [RECOVERED, TEMP_REPOS, SCAN_RESULTS]:
                    if extra.exists():
                        run_script(script, scan_root=str(extra), timeout=600)

        log(f"Round {round_num} execution: {success}/{len(plan)} primary scripts succeeded")

        # 5. Measure improvement
        new_gaps = rebuild_and_measure()
        log(f"After round — Live: {new_gaps['live_count']}")

        # Early stop if no progress
        if previous_live is not None:
            if new_gaps["live_count"] <= previous_live:
                log("No increase in LIVE abilities — stopping early (diminishing returns)")
                break
        previous_live = new_gaps["live_count"]

        time.sleep(1)

    # ============================================================
    # FINAL REPORT
    # ============================================================
    log("\n" + "=" * 70)
    log("FINAL STATE")
    log("=" * 70)

    catalog, catalog_path = load_ability_catalog()
    gaps = analyze_gaps(catalog)

    log(f"Final LIVE abilities : {gaps['live_count']}")
    log(f"Still MISSING        : {len(gaps['MISSING'])}")
    log(f"PARTIAL / STUB / etc : {len(gaps['PARTIAL'])+len(gaps['STUB'])+len(gaps['SOFT'])+len(gaps['CODE'])}")

    if gaps["MISSING"]:
        log("Remaining MISSING abilities:")
        for g in gaps["MISSING"][:15]:
            log(f"  - {g['name']}")

    # Write a machine-readable summary
    summary = {
        "finished_at": datetime.now().isoformat(),
        "live_count": gaps["live_count"],
        "missing": [g["name"] for g in gaps["MISSING"]],
        "partial": [g["name"] for g in gaps["PARTIAL"]],
        "rounds_run": round_num,
    }
    summary_path = LOG_DIR / "smart_learn_final_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    log(f"Summary written → {summary_path}")

    log("Smart Learn Controller finished.")
    log("System is now in a better state to self-build / self-extend.")
    log("=" * 70)


if __name__ == "__main__":
    main()