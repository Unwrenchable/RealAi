#!/usr/bin/env python3
import os
import shutil
import filecmp
import hashlib
import time
from pathlib import Path

# ---------------------------------------------------------
# CORRECT PATHS FOR YOUR CODESPACE
# ---------------------------------------------------------
CLEAN_ROOT = Path("/workspaces/RealAi")
MESSY_ROOT = Path("/workspaces/RealAi/realai_og_mess/realai")  # FIXED ROOT
BACKUP_ROOT = CLEAN_ROOT / ".backup"

IGNORE_NAMES = {
    ".git", "__pycache__", ".backup", ".venv", "node_modules", ".vscode"
}

def log(msg: str):
    print(msg)

def should_ignore(path: Path) -> bool:
    parts = set(p.name for p in path.parents) | {path.name}
    return any(name in IGNORE_NAMES for name in parts)

# ---------------------------------------------------------
# LINUX-SAFE BACKUP ENGINE
# ---------------------------------------------------------
def make_backup():
    BACKUP_ROOT.mkdir(exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    dest = BACKUP_ROOT / f"clean_backup_{ts}"
    log(f"[backup] Creating backup at: {dest}")

    dest.mkdir(parents=True, exist_ok=True)

    for root, dirs, files in os.walk(CLEAN_ROOT):
        root_path = Path(root)

        # Skip backup folder itself
        if BACKUP_ROOT in root_path.parents:
            continue

        # Skip ignored dirs
        dirs[:] = [d for d in dirs if d not in IGNORE_NAMES]

        for fname in files:
            src_file = root_path / fname
            if should_ignore(src_file):
                continue

            rel = src_file.relative_to(CLEAN_ROOT)
            dst_file = dest / rel
            dst_file.parent.mkdir(parents=True, exist_ok=True)

            try:
                shutil.copy2(src_file, dst_file)
            except Exception as e:
                log(f"[backup-warning] Could not copy {src_file}: {e}")

    log("[backup] Backup complete.")
    return dest

# ---------------------------------------------------------
# MERGE ENGINE HELPERS
# ---------------------------------------------------------
def hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def is_newer(src: Path, dst: Path) -> bool:
    if not dst.exists():
        return True
    src_m = src.stat().st_mtime
    dst_m = dst.stat().st_mtime
    if src_m > dst_m + 1e-6:
        return True
    return hash_file(src) != hash_file(dst)

# ---------------------------------------------------------
# SMART MERGE LOGIC
# ---------------------------------------------------------
def smart_merge_file(messy_file: Path, clean_file: Path):
    if not clean_file.exists():
        log(f"[merge] Missing in clean -> copy: {messy_file} -> {clean_file}")
        clean_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(messy_file, clean_file)
        return

    same = filecmp.cmp(str(messy_file), str(clean_file), shallow=False)
    if same:
        return

    if is_newer(messy_file, clean_file):
        log(f"[merge] Overwrite clean with messy (newer/different): {messy_file} -> {clean_file}")
        clean_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(messy_file, clean_file)
    else:
        log(f"[merge] Keep clean (clean considered newer): {clean_file}")

# ---------------------------------------------------------
# WALK BOTH REPOS AND MERGE
# ---------------------------------------------------------
def walk_and_merge():
    log(f"[info] CLEAN_ROOT: {CLEAN_ROOT}")
    log(f"[info] MESSY_ROOT: {MESSY_ROOT}")

    if not CLEAN_ROOT.is_dir():
        raise RuntimeError(f"Clean root not found: {CLEAN_ROOT}")
    if not MESSY_ROOT.is_dir():
        raise RuntimeError(f"Messy root not found: {MESSY_ROOT}")

    for root, dirs, files in os.walk(MESSY_ROOT):
        root_path = Path(root)

        dirs[:] = [d for d in dirs if not should_ignore(root_path / d)]

        for fname in files:
            messy_file = root_path / fname
            if should_ignore(messy_file):
                continue

            rel = messy_file.relative_to(MESSY_ROOT)
            clean_file = CLEAN_ROOT / rel

            smart_merge_file(messy_file, clean_file)

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():
    log("[start] SMART-MERGE RealAi engine")
    log("[step] Creating backup of clean repo...")
    make_backup()
    log("[step] Walking messy repo and merging into clean...")
    walk_and_merge()
    log("[done] Merge complete.")

if __name__ == "__main__":
    main()
