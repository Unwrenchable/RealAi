
import os, json, re, hashlib

ROOT = "C:\\realai"
OUT = "C:\\realai\\scan_results\\fs2_module_manifest.json"

MODULE_PATTERNS = [
    r"class\s+\w+",
    r"def\s+\w+",
    r"async\s+def\s+\w+",
    r"function\s+\w+",
    r"export\s+function\s+\w+",
    r"module\.exports",
    r"require\(",
    r"import\s+\w+",
    r"from\s+\w+\s+import",
    r"register_\w+",
    r"plugins?\s*=",
    r"capabilities?\s*=",
    r"tools?\s*=",
    r"agents?\s*=",
    r"memory\s*=",
    r"provider\s*=",
    r"engine\s*=",
    r"world\s*=",
    r"environment\s*="
]

EXTENSIONS = [
    ".py",".js",".ts",".json",".md",".txt",".yaml",".yml",".toml",".ini",".cfg"
]

def hash_file(path):
    try:
        with open(path,"rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except:
        return None

def scan_file(path):
    hits=[]
    try:
        with open(path,"r",encoding="utf-8",errors="ignore") as f:
            text=f.read()
    except:
        return hits

    for pattern in MODULE_PATTERNS:
        if re.search(pattern,text,re.IGNORECASE):
            hits.append({"pattern":pattern})
    return hits

def walk(root):
    manifest=[]
    for dp,_,files in os.walk(root):
        for f in files:
            if any(f.lower().endswith(ext) for ext in EXTENSIONS):
                full=os.path.join(dp,f)
                results=scan_file(full)
                if results:
                    manifest.append({
                        "file":full,
                        "hash":hash_file(full),
                        "hits":results
                    })
    return manifest

if __name__=="__main__":
    os.makedirs(os.path.dirname(OUT),exist_ok=True)
    manifest=walk(ROOT)
    with open(OUT,"w",encoding="utf-8") as f:
        json.dump(manifest,f,indent=2)
    print(f"[FS-2] Module Scan Complete → {OUT}")
