import json
from pathlib import Path
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

OUT = Path("realai/world_model/world_model.json")

IGNORE_DIR_NAMES = {
    "node_modules", ".venv", "venv", "__pycache__", ".git",
    ".backup", "realai_historical_backups", "archive",
    "RealAI_Recovery_SAFE", ".pytest_cache", "*.egg-info",
    "dist", "build", ".tox", ".mypy_cache", ".ruff_cache",
    "site-packages", "Lib", "Scripts",
    ".pnpm", "pnpm-store", ".yarn",
}

def should_skip(path: Path) -> bool:
    return any(part in IGNORE_DIR_NAMES for part in path.parts)

def safe_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

def try_parse_dict_literal(s: str):
    try:
        return json.loads(s)
    except Exception:
        pass
    try:
        cleaned = (
            s.replace("True", "true")
             .replace("False", "false")
             .replace("None", "null")
             .replace("'", '"')
        )
        return json.loads(cleaned)
    except Exception:
        return {}

def extract_python_registry(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {}

    patterns = [
        r"ABILITY_REGISTRY\s*=\s*({.*?})",
        r"TOOL_REGISTRY\s*=\s*({.*?})",
        r"TASK_REGISTRY\s*=\s*({.*?})",
        r"PLUGIN_REGISTRY\s*=\s*({.*?})",
        r"WORLD_MODEL\s*=\s*({.*?})",
        r"ABILITIES\s*=\s*({.*?})",
        r"TOOLS\s*=\s*({.*?})",
    ]

    merged = {}
    for pat in patterns:
        for m in re.findall(pat, text, flags=re.DOTALL):
            data = try_parse_dict_literal(m)
            if isinstance(data, dict):
                merged.update(data)
    return merged

def merge_payload(merged: dict, data, source: str = "") -> int:
    """
    Safely merge dict or list payloads into the world model.
    Returns number of items added.
    """
    added = 0
    if isinstance(data, dict):
        # Prefer a stable key if present, otherwise merge top-level
        if "name" in data or "id" in data:
            key = data.get("name") or data.get("id") or source
            merged[str(key)] = data
            added = 1
        else:
            before = len(merged)
            merged.update(data)
            added = len(merged) - before
    elif isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, dict):
                key = item.get("name") or item.get("id") or f"{source}[{i}]"
                merged[str(key)] = item
                added += 1
            else:
                # fallback for plain values
                merged[f"{source}[{i}]"] = item
                added += 1
    return added

def main():
    search_roots = [
        Path("recovered"),
        Path("realai"),
        Path("modules"),
        Path("imports"),
        Path("apps"),
        Path("temp_repos"),
        Path("temp"),
    ]

    merged = {}
    found_json = 0
    found_py = 0

    for root in search_roots:
        if not root.exists():
            continue
        print(f"[world-model] searching {root} ...")

        # JSON world model + registry fragments
        for pattern in ("world_model*.json", "*registry*.json"):
            for p in root.rglob(pattern):
                if should_skip(p):
                    continue
                data = safe_json(p)
                if data is None:
                    continue
                added = merge_payload(merged, data, source=p.stem)
                if added:
                    found_json += 1
                    print(f"  + JSON/REG {p} (+{added})")

        # Python registry fragments
        for p in root.rglob("*.py"):
            if should_skip(p):
                continue
            try:
                head = p.read_text(encoding="utf-8", errors="ignore")[:4000]
            except Exception:
                continue
            if not any(k in head for k in (
                "ABILITY_REGISTRY", "TOOL_REGISTRY", "TASK_REGISTRY",
                "PLUGIN_REGISTRY", "WORLD_MODEL", "ABILITIES", "TOOLS"
            )):
                continue

            data = extract_python_registry(p)
            if data:
                added = merge_payload(merged, data, source=p.stem)
                if added:
                    found_py += 1
                    print(f"  + PY   {p} (+{added})")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    print(f"[world-model] merged {found_json} JSON + {found_py} PY → {OUT} ({len(merged)} keys)")

if __name__ == "__main__":
    main()