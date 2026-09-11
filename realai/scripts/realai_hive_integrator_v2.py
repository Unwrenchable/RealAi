import os
import json
import subprocess
import shutil
import time
from pathlib import Path

# ============================================================
# RealAI Multi-Root Hive Integrator v2
# Smarter, safer, and actually usable
# ============================================================

MAIN_ROOT = r"C:\RealAI-clean"
SCRIPTS_DIR = os.path.join(MAIN_ROOT, "scripts")

ROOTS = [
    r"C:\RealAI-clean",
    r"D:\models",
    r"D:\realai_archives",
    r"C:\tools\realai",
    r"C:\llama-vulkan",
    r"C:\llama.cpp",
    r"C:\Users\tsmit\backups",
    r"C:\Users\tsmit\models",
    r"C:\tmp",
    r"C:\Users\tsmit\projects\realai-clean",
    r"C:\Users\tsmit\realai",
]

# Full heavy pipeline — only run on the main root
FULL_PHASES = [
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

# Lightweight phases for secondary roots
LIGHT_PHASES = [
    "scan_repos_for_realai.py",
    "promote_unified_realai.py",
    "curated_promote.py",
]

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    ".tox", ".mypy_cache", ".pytest_cache", "dist", "build",
    ".next", ".nuxt", "coverage", ".cache"
}

DRY_RUN = False          # Set to True to test without executing
MAX_FOLDERS_PER_ROOT = 80  # Safety limit


def run_script(script_name: str, scan_root: str = None, timeout: int = 900):
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    if not os.path.exists(script_path):
        print(f"  [skip] Script not found: {script_name}")
        return False

    args = ["python", script_path]
    if scan_root and script_name not in {
        "diff_imports_promote_allowlist.py",
        "curated_promote.py",
        "world_model_merger.py",
        "plugin_registry_builder.py",
        "wire_recovered.py",
        "unified_structure_validator.py",
        "self_heal_loop.py",
        "monitor_model.py"
    }:
        args += ["--scan-root", scan_root]

    print(f"  → {script_name}" + (f"  (root: {scan_root})" if scan_root else ""))

    if DRY_RUN:
        print("     [dry-run] skipped")
        return True

    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=MAIN_ROOT
        )
        if result.returncode == 0:
            print(f"     ✓ OK")
            return True
        else:
            print(f"     ✗ Failed (exit {result.returncode})")
            if result.stderr:
                print(f"       {result.stderr[:300]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"     ✗ Timeout after {timeout}s")
        return False
    except Exception as e:
        print(f"     ✗ Error: {e}")
        return False


def is_junk(path: str) -> bool:
    parts = Path(path).parts
    return any(p in SKIP_DIRS for p in parts)


def get_interesting_folders(root: str, max_folders: int = 80):
    """Find folders that look like they contain RealAI-related code."""
    interesting = []
    keywords = ("realai", "plugin", "ability", "agent", "orchestr", "world_model",
                "memory", "tools", "organs", "rackup", "aura")

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune junk
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        if is_junk(dirpath):
            continue

        lower = dirpath.lower()
        if any(k in lower for k in keywords) or any(f.endswith((".py", ".json")) for f in filenames):
            interesting.append(dirpath)

        if len(interesting) >= max_folders:
            break

    return interesting


def process_main_root():
    print("\n" + "="*60)
    print("MAIN ROOT — Full Pipeline")
    print("="*60)

    for phase in FULL_PHASES:
        success = run_script(phase, scan_root=MAIN_ROOT)
        if not success and phase in ("self_heal_loop.py", "monitor_model.py"):
            # Non-critical, continue
            continue


def process_secondary_root(root: str):
    print("\n" + "-"*60)
    print(f"SECONDARY ROOT: {root}")
    print("-"*60)

    folders = get_interesting_folders(root, max_folders=MAX_FOLDERS_PER_ROOT)
    print(f"Found {len(folders)} interesting folders (capped at {MAX_FOLDERS_PER_ROOT})")

    if not folders:
        print("  Nothing interesting found — skipping.")
        return

    for i, folder in enumerate(folders, 1):
        print(f"\n[{i}/{len(folders)}] {folder}")
        for phase in LIGHT_PHASES:
            run_script(phase, scan_root=folder)


def main():
    print("="*60)
    print("RealAI Multi-Root Hive Integrator v2")
    print(f"Dry-run mode: {DRY_RUN}")
    print("="*60)

    start = time.time()

    # 1. Always process the main root fully
    if os.path.exists(MAIN_ROOT):
        process_main_root()
    else:
        print(f"ERROR: Main root not found: {MAIN_ROOT}")
        return

    # 2. Process secondary roots lightly
    for root in ROOTS:
        if root == MAIN_ROOT:
            continue
        if os.path.exists(root):
            process_secondary_root(root)
        else:
            print(f"\n[skip] Root does not exist: {root}")

    elapsed = time.time() - start
    print("\n" + "="*60)
    print(f"Hive integration finished in {elapsed/60:.1f} minutes")
    print("="*60)


if __name__ == "__main__":
    main()