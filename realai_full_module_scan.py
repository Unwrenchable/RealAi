import os
import json
import hashlib
import re

ROOT = "."
OUT = "full_module_manifest.json"

# Module patterns (regex)
MODULE_PATTERNS = [
    r"class\s+\w+",                     # Python/JS classes
    r"def\s+\w+",                       # Python functions
    r"async\s+def\s+\w+",               # Python async functions
    r"function\s+\w+",                  # JS functions
    r"export\s+function\s+\w+",         # JS exports
    r"module\.exports",                 # Node module export
    r"require\(",                       # Node require()
    r"import\s+\w+",                    # Python/JS import
    r"from\s+\w+\s+import",             # Python from-import
    r"register_\w+",                    # register_agent, register_tool, etc.
    r"plugins?\s*=",                    # plugin definitions
    r"capabilities?\s*=",               # capability definitions
    r"tools?\s*=",                      # tool definitions
    r"agents?\s*=",                     # agent definitions
    r"memory\s*=",                      # memory definitions
    r"provider\s*=",                    # provider definitions
    r"engine\s*=",                      # engine definitions
    r"world\s*=",                       # world-model definitions
    r"environment\s*=",                 # environment definitions
]

def hash_file(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except:
        return None

def scan_file(path):
    hits = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except:
        return hits

    for pattern in MODULE_PATTERNS:
        if re.search(pattern, text):
            hits.append({
                "pattern": pattern,
                "path": path
            })
    return hits

def walk(root):
    manifest = []
    for dirpath, dirs, files in os.walk(root):
        for file in files:
            full = os.path.join(dirpath, file)
            results = scan_file(full)
            if results:
                manifest.append({
                    "file": full,
                    "hash": hash_file(full),
                    "hits": results
                })
    return manifest

if __name__ == "__main__":
    manifest = walk(ROOT)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"[full-module-scan] Complete. Output written to {OUT}")
