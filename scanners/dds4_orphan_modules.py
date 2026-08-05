import os, json, re, hashlib

ROOT = "C:\\realai"
OUT = "C:\\realai\\scan_results\\dds4_orphan_modules.json"

EXTENSIONS = [".py",".js",".ts",".json",".yaml",".yml",".toml"]

IMPORT_PATTERNS = [
    r"import\s+([a-zA-Z0-9_\.]+)",
    r"from\s+([a-zA-Z0-9_\.]+)\s+import",
    r"require\(['\"]([a-zA-Z0-9_\-/]+)['\"]\)",
    r"import\s+.*?from\s+['\"]([a-zA-Z0-9_\-/]+)['\"]"
]

def hash_file(path):
    try:
        with open(path,"rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except:
        return None

def collect_imports(root):
    imports = set()
    for dp,_,files in os.walk(root):
        for f in files:
            if any(f.lower().endswith(ext) for ext in EXTENSIONS):
                full = os.path.join(dp,f)
                try:
                    with open(full,"r",encoding="utf-8",errors="ignore") as fh:
                        text = fh.read()
                except:
                    continue
                for pattern in IMPORT_PATTERNS:
                    matches = re.findall(pattern, text)
                    for m in matches:
                        imports.add(m.split(".")[0].lower())
    return imports

def collect_modules(root):
    modules = set()
    for dp,_,files in os.walk(root):
        for f in files:
            if any(f.lower().endswith(ext) for ext in EXTENSIONS):
                name = os.path.splitext(f)[0].lower()
                modules.add(name)
    return modules

if __name__=="__main__":
    os.makedirs(os.path.dirname(OUT),exist_ok=True)

    imported = collect_imports(ROOT)
    modules = collect_modules(ROOT)

    orphaned = sorted(list(modules - imported))

    with open(OUT,"w",encoding="utf-8") as f:
        json.dump({
            "imported_modules": sorted(list(imported)),
            "existing_modules": sorted(list(modules)),
            "orphan_modules": orphaned
        }, f, indent=2)

    print(f"[DDS-4] Orphan Module Scan Complete ? {OUT}")
