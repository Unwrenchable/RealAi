import os, json, re, hashlib

ROOT = "C:\\realai"
OUT = "C:\\realai\\scan_results\\dds5_unused_features.json"

EXTENSIONS = [".py",".js",".ts"]

# Patterns to detect definitions
DEF_PATTERNS = [
    r"def\s+([a-zA-Z0-9_]+)",
    r"class\s+([a-zA-Z0-9_]+)",
    r"function\s+([a-zA-Z0-9_]+)",
]

# Patterns to detect usage
USE_PATTERNS = [
    r"([a-zA-Z0-9_]+)\(",
    r"new\s+([a-zA-Z0-9_]+)",
    r"\.([a-zA-Z0-9_]+)\(",
]

def hash_file(path):
    try:
        with open(path,"rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except:
        return None

def collect_definitions(root):
    defs = set()
    for dp,_,files in os.walk(root):
        for f in files:
            if any(f.lower().endswith(ext) for ext in EXTENSIONS):
                full = os.path.join(dp,f)
                try:
                    with open(full,"r",encoding="utf-8",errors="ignore") as fh:
                        text = fh.read()
                except:
                    continue
                for pattern in DEF_PATTERNS:
                    matches = re.findall(pattern, text)
                    for m in matches:
                        defs.add(m.lower())
    return defs

def collect_usages(root):
    uses = set()
    for dp,_,files in os.walk(root):
        for f in files:
            if any(f.lower().endswith(ext) for ext in EXTENSIONS):
                full = os.path.join(dp,f)
                try:
                    with open(full,"r",encoding="utf-8",errors="ignore") as fh:
                        text = fh.read()
                except:
                    continue
                for pattern in USE_PATTERNS:
                    matches = re.findall(pattern, text)
                    for m in matches:
                        uses.add(m.lower())
    return uses

if __name__=="__main__":
    os.makedirs(os.path.dirname(OUT),exist_ok=True)

    defs = collect_definitions(ROOT)
    uses = collect_usages(ROOT)

    unused = sorted(list(defs - uses))

    with open(OUT,"w",encoding="utf-8") as f:
        json.dump({
            "definitions": sorted(list(defs)),
            "usages": sorted(list(uses)),
            "unused_features": unused
        }, f, indent=2)

    print(f"[DDS-5] Unused Feature Scan Complete ? {OUT}")
