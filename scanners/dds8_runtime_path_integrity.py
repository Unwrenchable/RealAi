import os, re, json

ROOT = "C:\\realai"
OUT = "C:\\realai\\scan_results\\dds8_runtime_path_integrity.json"

CODE_EXT = [".py", ".js", ".ts"]

IMPORT_PATTERNS = [
    r"from\s+([A-Za-z0-9_\.]+)\s+import",
    r"import\s+([A-Za-z0-9_\.]+)",
    r"require\(['\"]([^'\"]+)['\"]\)",
    r"from\s+['\"]([^'\"]+)['\"]"
]

RELATIVE_PATTERNS = [
    r"['\"](\./[^'\"]+)['\"]",
    r"['\"](\../[^'\"]+)['\"]"
]

def safe_read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except:
        return ""

def collect_code_files(root):
    collected = []
    for dp, _, files in os.walk(root):
        for f in files:
            if any(f.lower().endswith(ext) for ext in CODE_EXT):
                collected.append(os.path.join(dp, f))
    return collected

def normalize_path(p):
    return p.replace("\\", "/")

def module_to_path(module):
    """
    Convert Python-style module paths to file paths.
    Example: realai.agents.devops_agent -> realai/agents/devops_agent.py
    """
    parts = module.split(".")
    return "/".join(parts) + ".py"

def run_scan():
    code_files = collect_code_files(ROOT)
    all_paths = set()

    for dp, _, files in os.walk(ROOT):
        for f in files:
            full = os.path.join(dp, f)
            rel = os.path.relpath(full, ROOT)
            all_paths.add(normalize_path(rel.lower()))

    results = []

    for cf in code_files:
        rel_cf = normalize_path(os.path.relpath(cf, ROOT).lower())
        text = safe_read(cf)

        # IMPORTS
        for pattern in IMPORT_PATTERNS:
            matches = re.findall(pattern, text)
            for m in matches:
                mod_path = module_to_path(m.lower())
                if mod_path not in all_paths:
                    results.append({
                        "type": "missing_import_target",
                        "file": rel_cf,
                        "import": m,
                        "expected_path": mod_path
                    })

        # RELATIVE PATHS
        for pattern in RELATIVE_PATTERNS:
            matches = re.findall(pattern, text)
            for m in matches:
                rel_target = normalize_path(os.path.join(os.path.dirname(rel_cf), m)).lower()
                if rel_target not in all_paths:
                    results.append({
                        "type": "missing_relative_path",
                        "file": rel_cf,
                        "relative": m,
                        "expected_path": rel_target
                    })

    return results

if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    results = run_scan()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"[DDS-8] Runtime Path Integrity Scan Complete → {OUT}")
