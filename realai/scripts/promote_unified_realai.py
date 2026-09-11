import json
import shutil
import hashlib
from pathlib import Path
from datetime import datetime

CANDIDATES = Path("recovered") / "REALAI_SELF_IMPROVE_CANDIDATES.json"
HOME = Path(__file__).resolve().parents[1]

PROMOTE_MAP = {
    "agent_runtime": HOME / "realai" / "agent_runtime",
    "world_model":   HOME / "realai" / "world_model",
    "plugins":       HOME / "realai" / "plugins",
    "memory":        HOME / "realai" / "memory",
    "tools":         HOME / "realai" / "plugins" / "tools",
    "vscode":        HOME / "apps" / "vscode",
    "dashboard":     HOME / "apps" / "dashboard",
    "core":          HOME / "realai",
}

SKIP_PATH_PARTS = {
    "node_modules", ".pnpm", "dist", "build", ".next", "__pycache__",
    ".git", "venv", ".venv", "models", "target", "bin", "obj",
    ".cache", "coverage", ".turbo"
}

ALLOWED_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md", ".toml", ".yaml", ".yml"}

def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def should_skip(rel: str) -> bool:
    parts = Path(rel).parts
    if any(p in SKIP_PATH_PARTS for p in parts):
        return True
    if Path(rel).suffix.lower() not in ALLOWED_EXTS:
        return True
    return False

def classify(rel: str) -> str | None:
    rel_l = rel.lower().replace("\\", "/")
    if should_skip(rel):
        return None

    if any(k in rel_l for k in ("agent_runtime", "agent-runtime", "agent_runtime")):
        return "agent_runtime"
    if any(k in rel_l for k in ("world_model", "world-model")):
        return "world_model"
    if any(k in rel_l for k in ("/plugins/", "plugin_", "plugins/")):
        return "plugins"
    if any(k in rel_l for k in ("memory", "aura_memory", "aura-memory")):
        return "memory"
    if any(k in rel_l for k in ("/tools/", "tool_", "device_selector")):
        return "tools"
    if any(k in rel_l for k in ("vscode", "extension")):
        return "vscode"
    if "dashboard" in rel_l and any(k in rel_l for k in ("apps/", "frontend")):
        return "dashboard"
    if any(k in rel_l for k in ("realai/", "orchestr", "self_heal", "dispatcher")):
        return "core"
    return None

def should_promote(src: Path, dst: Path) -> bool:
    """Only promote if destination is missing or source looks better."""
    if not dst.exists():
        return True
    try:
        # Prefer newer or significantly larger files
        src_stat = src.stat()
        dst_stat = dst.stat()
        if src_stat.st_mtime > dst_stat.st_mtime + 60:  # clearly newer
            return True
        if src_stat.st_size > dst_stat.st_size * 1.2:   # significantly larger
            return True
        # Same size + same hash → skip
        if src_stat.st_size == dst_stat.st_size and file_hash(src) == file_hash(dst):
            return False
    except Exception:
        return True
    return False

def main():
    if not CANDIDATES.is_file():
        print("[promote] missing:", CANDIDATES)
        return

    data = json.loads(CANDIDATES.read_text(encoding="utf-8"))
    print(f"[promote] {len(data)} candidates to evaluate...")

    promoted = 0
    skipped = 0
    log_entries = []

    for hit in data:
        try:
            root = Path(hit["root"])
            rel = hit["rel"]
        except Exception:
            skipped += 1
            continue

        kind = classify(rel)
        if not kind:
            skipped += 1
            continue

        src = root / rel
        if not src.exists() or not src.is_file():
            skipped += 1
            continue

        dst_root = PROMOTE_MAP[kind]
        dst_root.mkdir(parents=True, exist_ok=True)

        # Keep some directory structure to avoid collisions
        # Use the last 2 path parts when possible
        parts = Path(rel).parts
        if len(parts) >= 2:
            dst = dst_root / parts[-2] / parts[-1]
        else:
            dst = dst_root / Path(rel).name

        dst.parent.mkdir(parents=True, exist_ok=True)

        if not should_promote(src, dst):
            skipped += 1
            continue

        try:
            shutil.copy2(src, dst)
            print(f"[promote] {kind:15} {rel}")
            promoted += 1
            log_entries.append({"kind": kind, "src": str(src), "dst": str(dst)})
        except Exception as e:
            print(f"[promote] failed {src}: {e}")
            skipped += 1

    # Write a small promote log
    log_path = HOME / "recovered" / "PROMOTE_SMART_LOG.json"
    log_path.write_text(json.dumps({
        "timestamp": datetime.now().isoformat(),
        "promoted": promoted,
        "skipped": skipped,
        "entries": log_entries
    }, indent=2), encoding="utf-8")

    print(f"\n[promote] done. promoted={promoted} skipped={skipped}")
    print(f"[promote] log → {log_path}")

if __name__ == "__main__":
    main()