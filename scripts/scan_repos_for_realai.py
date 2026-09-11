import json
import hashlib
from pathlib import Path
from datetime import datetime
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

SKIP_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "env",
    "models", ".cache", ".pytest_cache", "dist", "build", ".next",
    "target", "bin", "obj", ".idea", ".vscode", ".pnpm", ".turbo",
    "coverage", ".mypy_cache", ".tox"
}

SKIP_EXTS = {
    ".pyc", ".pyo", ".so", ".dll", ".exe", ".bin", ".gguf",
    ".safetensors", ".pt", ".pth", ".onnx", ".log", ".tmp",
    ".bak", ".swp", ".DS_Store"
}

# Keywords that make a file more interesting for RealAI recovery
INTERESTING_KEYWORDS = (
    "ability", "plugin", "agent", "orchestr", "world_model", "memory",
    "aura", "self_heal", "dispatch", "registry", "catalog", "tool",
    "organ", "rackup", "promote", "wire", "server", "route", "api"
)

ALLOWED_EXTS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md", ".toml",
    ".yaml", ".yml", ".txt", ".ini", ".cfg"
}

def should_skip(p: Path) -> bool:
    # Skip by directory name
    if any(part in SKIP_DIRS for part in p.parts):
        return True
    if p.suffix.lower() in SKIP_EXTS:
        return True
    return False

def score_file(path: Path, rel: str) -> int:
    """Simple interestingness score so we can rank results later."""
    score = 0
    name_l = path.name.lower()
    rel_l = rel.lower().replace("\\", "/")

    if path.suffix.lower() in {".py", ".ts", ".js", ".json"}:
        score += 3
    if path.suffix.lower() == ".md":
        score += 1

    for kw in INTERESTING_KEYWORDS:
        if kw in name_l or kw in rel_l:
            score += 5

    # Bonus for being in important-looking folders
    if any(x in rel_l for x in ("realai/", "plugins/", "agent", "world_model", "ability")):
        score += 4

    return score

def scan_root(root: Path, max_files: int = 80000) -> dict:
    items = []
    count = 0
    truncated = False

    for p in root.rglob("*"):
        if should_skip(p):
            continue
        try:
            if not p.is_file():
                continue

            # Prefer source / config files
            if p.suffix.lower() not in ALLOWED_EXTS and p.suffix.lower() not in {".md", ".txt"}:
                # still allow some others but with low priority
                if p.suffix.lower() not in {".json"}:
                    continue

            rel = str(p.relative_to(root))
            stat = p.stat()

            item = {
                "root": str(root),
                "rel": rel,
                "name": p.name,
                "ext": p.suffix.lower(),
                "size": stat.st_size,
                "mtime": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "score": score_file(p, rel),
            }
            items.append(item)
            count += 1

            if count >= max_files:
                truncated = True
                break
        except Exception:
            continue

    # Sort by interestingness so the best files appear first
    items.sort(key=lambda x: x["score"], reverse=True)

    return {
        "root": str(root),
        "file_count": len(items),
        "truncated": truncated,
        "files": items,
    }

def _scan_out_dirs() -> list[Path]:
    """Prefer scripts/recovered (stable after archive move); also mirror to recovered/."""
    dirs = [Path("scripts") / "recovered", Path("recovered")]
    for d in dirs:
        try:
            d.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
    return [d for d in dirs if d.is_dir()]


def _good_code_candidates() -> list[Path]:
    """Prefer live product trees + gold import packages (from catalog if present)."""
    base = [
        Path("abilities"),
        Path("adapters"),
        Path("agent_tools"),
        Path("agents"),
        Path("aura"),
        Path("core"),
        Path("modules"),
        Path("plugins"),
        Path("realai"),
        Path("scripts"),
        Path("tools"),
        Path("training"),
        Path("apps"),
        Path("scan_results"),
        Path("scripts") / "recovered",
        Path("recovered"),
        # High-signal gold / unique imports (not bulk recovered dumps)
        Path("imports") / "external" / "unique-modules",
        Path("imports") / "external" / "agent_tools_gold",
        Path("imports") / "external" / "C_realai_modules",
        Path("imports") / "external" / "C_realai_plugins",
        Path("imports") / "external" / "C_realai_server",
        Path("imports") / "external" / "orchestrators",
        Path("imports") / "external" / "self_improvement",
        Path("imports") / "external" / "organs",
        Path("imports") / "external" / "agents_advanced",
        Path("imports") / "external" / "desktop_unique",
        Path("imports") / "external" / "grok_export_realai",
        Path("imports") / "external" / "recovery_plugins",
        Path("imports"),
        Path("temp_repos"),
    ]
    # Merge present_roots from prior catalog pass
    for cat in (
        Path("scan_results") / "GOOD_CODE_ROOTS.json",
        Path("recovered") / "GOOD_CODE_ROOTS.json",
    ):
        if not cat.is_file():
            continue
        try:
            data = json.loads(cat.read_text(encoding="utf-8"))
            for rel in data.get("present_roots") or []:
                p = Path(str(rel))
                if p not in base:
                    base.append(p)
        except Exception:
            pass
    return base


def main():
    candidates = _good_code_candidates()

    roots = [p.resolve() for p in candidates if p.exists()]
    # de-dupe while preserving order
    seen = set()
    uniq = []
    for r in roots:
        key = str(r).lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    roots = uniq
    print(f"[scan] scanning {len(roots)} roots (good-code aware)...")

    report = []
    total_files = 0
    high_score = 0

    for r in roots:
        print(f"[scan] → {r}")
        result = scan_root(r)
        report.append(result)
        total_files += result["file_count"]
        high_score += sum(1 for f in result["files"] if f["score"] >= 8)
        print(f"       found {result['file_count']} files "
              f"(high-value ≈ {sum(1 for f in result['files'] if f['score'] >= 8)})")

    summary = {
        "scanned_at": datetime.now().isoformat(),
        "total_files": total_files,
        "high_value_files": high_score,
        "roots": report,
    }
    payload = json.dumps(summary, indent=2)

    wrote = []
    for d in _scan_out_dirs():
        out = d / "REALAI_REPO_SCAN.json"
        out.write_text(payload, encoding="utf-8")
        wrote.append(str(out))

    print(f"\n[scan] wrote {wrote}")
    print(f"[scan] total files indexed: {total_files}")
    print(f"[scan] high-value files   : {high_score}")

if __name__ == "__main__":
    main()