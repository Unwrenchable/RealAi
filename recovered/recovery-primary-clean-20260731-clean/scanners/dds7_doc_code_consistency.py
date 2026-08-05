import os, re, json

ROOT = "C:\\realai"
OUT = "C:\\realai\\scan_results\\dds7_doc_code_consistency.json"

DOC_EXT = [".md"]
CODE_EXT = [".py", ".js", ".ts"]

# Patterns to detect features in docs
DOC_PATTERNS = {
    "agent": r"\bagent[s]?\b",
    "memory": r"\bmemory\b",
    "tool": r"\btool[s]?\b",
    "skill": r"\bskill[s]?\b",
    "provider": r"\bprovider[s]?\b",
    "model": r"\bmodel[s]?\b",
    "route": r"/[a-zA-Z0-9_/]+"
}

# Patterns to detect features in code
CODE_PATTERNS = {
    "agent": r"class\s+([A-Za-z0-9_]*Agent)",
    "memory": r"class\s+([A-Za-z0-9_]*Memory)",
    "tool": r"class\s+([A-Za-z0-9_]*Tool)",
    "skill": r"class\s+([A-Za-z0-9_]*Skill)",
    "provider": r"class\s+([A-Za-z0-9_]*Provider)",
    "model": r"class\s+([A-Za-z0-9_]*Model)",
    "route": r"@app\.route\(['\"]([^'\"]+)['\"]"
}

def safe_read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except:
        return ""

def collect_files(root, exts):
    collected = []
    for dp, _, files in os.walk(root):
        for f in files:
            if any(f.lower().endswith(ext) for ext in exts):
                collected.append(os.path.join(dp, f))
    return collected

def extract_doc_features(text):
    found = {}
    for key, pattern in DOC_PATTERNS.items():
        matches = re.findall(pattern, text, flags=re.IGNORECASE)
        found[key] = list(set(matches))
    return found

def extract_code_features(text):
    found = {}
    for key, pattern in CODE_PATTERNS.items():
        matches = re.findall(pattern, text)
        found[key] = list(set(matches))
    return found

def run_scan():
    docs = collect_files(ROOT, DOC_EXT)
    code = collect_files(ROOT, CODE_EXT)

    doc_features = {}
    code_features = {}

    # Extract doc features
    for d in docs:
        text = safe_read(d)
        doc_features[d] = extract_doc_features(text)

    # Extract code features
    for c in code:
        text = safe_read(c)
        code_features[c] = extract_code_features(text)

    # Build global sets
    global_doc = {k: set() for k in DOC_PATTERNS.keys()}
    global_code = {k: set() for k in CODE_PATTERNS.keys()}

    for d, feats in doc_features.items():
        for k, vals in feats.items():
            global_doc[k].update(vals)

    for c, feats in code_features.items():
        for k, vals in feats.items():
            global_code[k].update(vals)

    # Compare
    results = []

    for key in DOC_PATTERNS.keys():
        documented = global_doc[key]
        implemented = global_code[key]

        # Documented but not implemented
        for item in documented:
            if item not in implemented:
                results.append({
                    "type": "documented_not_implemented",
                    "category": key,
                    "item": item
                })

        # Implemented but not documented
        for item in implemented:
            if item not in documented:
                results.append({
                    "type": "implemented_not_documented",
                    "category": key,
                    "item": item
                })

    return results

if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    results = run_scan()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"[DDS-7] Doc ↔ Code Consistency Scan Complete → {OUT}")
