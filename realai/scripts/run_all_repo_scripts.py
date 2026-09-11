#!/usr/bin/env python3
"""
Discover and run Python scripts across the RealAI tree.

Default (no flags) = curated ALLOWLIST + EXECUTE (safe real work).
  python scripts/run_all_repo_scripts.py

Dry-run / discovery:
  python scripts/run_all_repo_scripts.py --dry-run
  python scripts/run_all_repo_scripts.py --discover --interesting-only
  python scripts/run_all_repo_scripts.py --under scripts --execute

Skips junk / recovery dumps for --discover walks.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]  # C:\RealAI-clean

IGNORE_DIR_NAMES = {
    "node_modules", ".venv", "venv", "__pycache__", ".git",
    ".backup", "realai_historical_backups", "archive",
    "RealAI_Recovery_SAFE", ".pytest_cache", "dist", "build",
    ".tox", ".mypy_cache", ".ruff_cache", "site-packages",
    "Lib", "Scripts", ".pnpm", "pnpm-store", ".yarn",
    "models",
}

IGNORE_SUBSTRINGS = (
    "site-packages",
    ".venv",
    "venv_lib",
    "node_modules",
    "__pycache__",
    "realai_og_mess",
    "realai_archive",
    ".backup",
    "typing_extensions",
    "pip__vendor",
    "pydantic_plugin",
    "kilo_worktrees",
)

# Bulk dumps — never walk for auto-run discovery
SKIP_TREE_MARKERS = (
    "temp_repos",
    "recovered",
    "imports\\external",
    "imports/external",
    "apps\\vscode",
    "apps/vscode",
    "RealAI_Recovery_SAFE",
    "realai_historical_backups",
)

INTERESTING = (
    "scan", "find", "lost", "promote", "unify", "merge", "world",
    "plugin", "registry", "valid", "monitor", "heal", "ability",
    "wire", "server", "recover", "self_improve", "self-improve",
    "dispatch", "catalog", "organ", "doctor", "gap", "bootstrap",
    "import", "phase", "curated", "allowlist", "auto_wire", "good_code",
)

HARD_SKIP_NAMES = {
    "setup.py", "conftest.py", "__init__.py", "manage.py",
    "wsgi.py", "asgi.py", "settings.py",
    "run_all_repo_scripts.py",
}

# Curated safe entry points (relative to ROOT) — default execute set
ALLOWLIST = [
    "scripts/catalog_good_code_roots.py",
    "scripts/walk_root.py",
    "tools/walk_root.py",
    "scripts/organize_repo.py",
    "scripts/deep_unify_walk.py",
    "scripts/wire_training.py",
    "scripts/walk_training_sources.py",
    "scripts/dispatch_training.py",
    "scripts/amd_stack_status.py",
    "scripts/train_lora_local.py",
    "scripts/train_to_chat_gguf.py",
    "scripts/scan_repos_for_realai.py",
    "scripts/find_self_improve_and_lost.py",
    "scripts/promote_unified_realai.py",
    "scripts/diff_imports_promote_allowlist.py",
    "scripts/curated_promote.py",
    "scripts/deep_promote_scan.py",
    "scripts/deep_promote_wire.py",
    "scripts/world_model_merger.py",
    "scripts/plugin_registry_builder.py",
    "scripts/wire_recovered.py",
    "scripts/unified_structure_validator.py",
    "scripts/self_heal_loop.py",
    "scripts/monitor_model.py",
    "scripts/import_external_trees.py",
    "scripts/heal_cli.py",
    "realai/ability_catalog.py",
    "realai/doctor.py",
    "realai/plugin_marketplace.py",
    "realai/self_heal.py",
    "realai/self_improvement.py",
    "realai/recovery_registry.py",
    "abilities/auto_wire.py",
    "agent_tools/registry.py",
    "agent_tools/importer.py",
]


def should_skip_path(path: Path) -> bool:
    parts = path.parts
    if any(part in IGNORE_DIR_NAMES for part in parts):
        return True
    joined = "\\".join(parts).lower().replace("/", "\\")
    if any(s in joined for s in IGNORE_SUBSTRINGS):
        return True
    if any(s.lower() in joined for s in SKIP_TREE_MARKERS):
        return True
    # Flattened backup-style filenames inside plugins/
    name = path.name.lower()
    if name.startswith("c__realai") or "backup_clean_backup" in name:
        return True
    return False


def discover_scripts(root: Path) -> list[Path]:
    found: list[Path] = []
    for p in root.rglob("*.py"):
        if should_skip_path(p):
            continue
        if p.name in HARD_SKIP_NAMES:
            continue
        if p.resolve() == Path(__file__).resolve():
            continue
        found.append(p)
    return sorted(found)


def is_interesting(p: Path) -> bool:
    return any(k in p.name.lower() for k in INTERESTING)


def run_one(script: Path, timeout: int, cwd: Path) -> dict:
    t0 = time.time()
    res = {
        "script": str(script.relative_to(ROOT)) if script.is_relative_to(ROOT) else str(script),
        "ok": False,
        "seconds": 0.0,
        "returncode": None,
        "stdout_tail": "",
        "stderr_tail": "",
        "error": None,
    }
    try:
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        res["returncode"] = completed.returncode
        res["ok"] = completed.returncode == 0
        res["stdout_tail"] = (completed.stdout or "")[-1500:]
        res["stderr_tail"] = (completed.stderr or "")[-800:]
    except subprocess.TimeoutExpired:
        res["error"] = f"timeout>{timeout}s"
    except Exception as e:
        res["error"] = f"{type(e).__name__}: {e}"
    res["seconds"] = round(time.time() - t0, 2)
    return res


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Run curated RealAI scripts (default) or discover/execute more"
    )
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="List only; do not execute (overrides default execute)",
    )
    ap.add_argument(
        "--execute",
        action="store_true",
        help="Force execute (default already executes allowlist)",
    )
    ap.add_argument(
        "--discover",
        action="store_true",
        help="Walk the tree instead of curated allowlist (dry-run unless --execute)",
    )
    ap.add_argument("--interesting-only", action="store_true", help="Filter by recovery-ish names")
    ap.add_argument(
        "--allowlist",
        action="store_true",
        help="Only curated safe entry points (default when not discovering)",
    )
    ap.add_argument("--under", default="", help="Subpath only, e.g. scripts | realai | modules")
    ap.add_argument("--timeout", type=int, default=300, help="Per-script timeout seconds")
    ap.add_argument("--limit", type=int, default=0, help="Max scripts (0 = no limit)")
    ap.add_argument("--cwd-home", action="store_true", default=True, help="cwd=ROOT (default on)")
    args = ap.parse_args()

    use_discover = bool(args.discover or args.under or args.interesting_only)
    use_allowlist = bool(args.allowlist) or not use_discover

    # Default = execute allowlist. Discover walks stay dry unless --execute.
    do_execute = (not args.dry_run) and (use_allowlist or args.execute)
    if use_discover and not args.execute and not args.dry_run:
        # explicit: discover without --execute → dry-run for safety
        do_execute = False

    root = ROOT
    if use_allowlist and not (args.discover or args.under):
        scripts: list[Path] = []
        for rel in ALLOWLIST:
            p = ROOT / rel
            if p.is_file():
                scripts.append(p)
            else:
                print(f"[skip missing] {rel}")
        print(f"[allowlist] {len(scripts)} script(s) present")
    else:
        if args.under:
            root = (ROOT / args.under).resolve()
            if not root.exists():
                print(f"[error] under path not found: {root}")
                return 1
        scripts = discover_scripts(root)
        if args.interesting_only:
            scripts = [p for p in scripts if is_interesting(p)]

    mode = "allowlist" if (use_allowlist and not (args.discover or args.under)) else "discover"
    print(f"[mode] {mode} execute={do_execute}")
    print(f"[discover] root={ROOT if mode == 'allowlist' else root}")
    print(f"[discover] found {len(scripts)} script(s)")
    for p in scripts[:60]:
        try:
            rel = p.relative_to(ROOT)
        except ValueError:
            rel = p
        mark = "*" if is_interesting(p) else " "
        print(f"  {mark} {rel}")
    if len(scripts) > 60:
        print(f"  ... and {len(scripts) - 60} more")

    if not do_execute:
        print("\n[dry-run] Nothing executed.")
        print("Examples:")
        print("  python scripts/run_all_repo_scripts.py")
        print("  python scripts/run_all_repo_scripts.py --dry-run")
        print("  python scripts/run_all_repo_scripts.py --discover --interesting-only --execute")
        print("  python scripts/run_all_repo_scripts.py --under scripts --execute --timeout 300")
        return 0

    to_run = scripts[: args.limit] if args.limit > 0 else scripts
    ok = fail = 0
    for i, script in enumerate(to_run, 1):
        cwd = ROOT if args.cwd_home else script.parent
        try:
            rel = script.relative_to(ROOT)
        except ValueError:
            rel = script
        print(f"\n[{i}/{len(to_run)}] RUN {rel} (timeout={args.timeout}s)")
        r = run_one(script, args.timeout, cwd)
        if r["ok"]:
            ok += 1
            print(f"  OK  ({r['seconds']}s)")
            if r["stdout_tail"].strip():
                for ln in r["stdout_tail"].strip().splitlines()[-3:]:
                    print(f"    out> {ln[:160]}")
        else:
            fail += 1
            print(f"  FAIL ({r['seconds']}s) rc={r['returncode']} err={r['error']}")
            if r["stderr_tail"].strip():
                for ln in r["stderr_tail"].strip().splitlines()[-3:]:
                    print(f"    err> {ln[:160]}")

    print(f"\n[summary] ran={len(to_run)} ok={ok} fail={fail}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())