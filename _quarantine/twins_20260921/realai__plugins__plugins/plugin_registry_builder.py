import json
from pathlib import Path
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

REGISTRY = Path("realai/plugins/registry.json")

# All places we want to hunt for plugins / abilities — including nested repos
SEARCH_ROOTS = [
    Path("realai"),
    Path("modules"),
    Path("imports"),
    Path("recovered"),
    Path("apps"),
    Path("temp_repos"),          # nested repos live here
    Path("temp"),                # extra place you mentioned
]

# Aggressive ignore list — critical so nested scans stay fast
IGNORE_DIR_NAMES = {
    "node_modules", ".venv", "venv", "__pycache__", ".git",
    ".backup", "realai_historical_backups", "archive",
    "RealAI_Recovery_SAFE", ".pytest_cache", "*.egg-info",
    "dist", "build", ".tox", ".mypy_cache", ".ruff_cache",
    "site-packages", "Lib", "Scripts",
    ".pnpm", "pnpm-store", ".yarn",
}

def should_skip(path: Path) -> bool:
    """Skip any path that contains a known junk directory name."""
    return any(part in IGNORE_DIR_NAMES for part in path.parts)

def safe_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}

def extract_python_plugin(path: Path):
    """
    Extract plugin metadata from Python files.
    Looks for PLUGIN / PLUGIN_MANIFEST style dicts.
    Tolerates imperfect Python literals.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    patterns = [
        r"PLUGIN\s*=\s*({.*?})",
        r"PLUGIN_MANIFEST\s*=\s*({.*?})",
        r"plugin_manifest\s*=\s*({.*?})",
        r"ABILITY\s*=\s*({.*?})",
        r"ABILITY_MANIFEST\s*=\s*({.*?})",
    ]

    for pat in patterns:
        for m in re.findall(pat, text, flags=re.DOTALL):
            # Try strict JSON first
            try:
                return json.loads(m)
            except Exception:
                pass
            # Light Python → JSON conversion
            try:
                cleaned = (
                    m.replace("True", "true")
                     .replace("False", "false")
                     .replace("None", "null")
                     .replace("'", '"')
                )
                return json.loads(cleaned)
            except Exception:
                continue
    return None

def find_plugins():
    plugins = []
    seen = set()

    for root in SEARCH_ROOTS:
        if not root.exists():
            continue

        print(f"[registry] scanning {root} (nested + deep) ...")

        # JSON plugin manifests (anywhere under the root, including nested repos)
        for p in root.rglob("plugin*.json"):
            if should_skip(p):
                continue
            data = safe_json(p)
            if not data:
                continue
            name = data.get("name", p.stem)
            if name in seen:
                continue
            seen.add(name)
            plugins.append({
                "source": str(p),
                "name": name,
                "version": data.get("version", "unknown"),
                "capabilities": data.get("capabilities", []),
            })
            print(f"  + JSON {p}")

        # Also catch ability / tool style jsons that may not start with "plugin"
        for p in root.rglob("*ability*.json"):
            if should_skip(p):
                continue
            data = safe_json(p)
            if not data:
                continue
            name = data.get("name", p.stem)
            if name in seen:
                continue
            seen.add(name)
            plugins.append({
                "source": str(p),
                "name": name,
                "version": data.get("version", "unknown"),
                "capabilities": data.get("capabilities", data.get("abilities", [])),
            })
            print(f"  + ABIL {p}")

        # Python plugin / ability manifests
        for p in root.rglob("plugin*.py"):
            if should_skip(p):
                continue
            data = extract_python_plugin(p)
            if not data:
                continue
            name = data.get("name", p.stem)
            if name in seen:
                continue
            seen.add(name)
            plugins.append({
                "source": str(p),
                "name": name,
                "version": data.get("version", "unknown"),
                "capabilities": data.get("capabilities", []),
            })
            print(f"  + PY   {p}")

        # Catch ability-style Python files too
        for p in root.rglob("*ability*.py"):
            if should_skip(p):
                continue
            data = extract_python_plugin(p)
            if not data:
                continue
            name = data.get("name", p.stem)
            if name in seen:
                continue
            seen.add(name)
            plugins.append({
                "source": str(p),
                "name": name,
                "version": data.get("version", "unknown"),
                "capabilities": data.get("capabilities", []),
            })
            print(f"  + PY-A {p}")

    return plugins

def main():
    plugins = find_plugins()
    REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(plugins, indent=2), encoding="utf-8")
    print(f"[registry] wrote {REGISTRY} ({len(plugins)} plugins)")

if __name__ == "__main__":
    main()