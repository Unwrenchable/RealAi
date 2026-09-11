import os, re, json

ROOT = "C:\\realai"
OUT = "C:\\realai\\scan_results\\dds9_subsystem_completeness_deep.json"

# Subsystem signatures
SUBSYSTEM_SIG = {
    "agents": ["agent", "agents"],
    "memory": ["memory"],
    "tools": ["tool", "tools"],
    "providers": ["provider", "providers"],
    "models": ["model", "models"],
    "sdk": ["sdk"],
    "cli": ["cli"],
    "fusion_ui": ["fusion-ui", "fusion_ui", "fusionui"]
}

# Class patterns
CLASS_PATTERNS = {
    "agents": r"class\s+([A-Za-z0-9_]*Agent)",
    "memory": r"class\s+([A-Za-z0-9_]*Memory)",
    "tools": r"class\s+([A-Za-z0-9_]*Tool)",
    "providers": r"class\s+([A-Za-z0-9_]*Provider)",
    "models": r"class\s+([A-Za-z0-9_]*Model)",
    "sdk": r"class\s+([A-Za-z0-9_]*SDK)",
    "cli": r"class\s+([A-Za-z0-9_]*CLI)",
    "fusion_ui": r"class\s+([A-Za-z0-9_]*UI)"
}

CODE_EXT = [".py", ".js", ".ts"]

def safe_read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except:
        return ""

def detect_subsystem(path):
    """Detect subsystem by directory name."""
    lp = path.lower().replace("\\", "/")
    for sub, sigs in SUBSYSTEM_SIG.items():
        for s in sigs:
            if f"/{s}/" in lp or lp.endswith(f"/{s}"):
                return sub
    return None

def run_scan():
    subsystems = {k: {"dirs": set(), "files": set(), "classes": set()} for k in SUBSYSTEM_SIG.keys()}

    # Walk entire repo
    for dp, _, files in os.walk(ROOT):
        rel_dp = dp.replace(ROOT, "").replace("\\", "/")
        sub = detect_subsystem(rel_dp)

        for f in files:
            if any(f.lower().endswith(ext) for ext in CODE_EXT):
                full = os.path.join(dp, f)
                rel = full.replace(ROOT, "").replace("\\", "/")

                if sub:
                    subsystems[sub]["dirs"].add(rel_dp)
                    subsystems[sub]["files"].add(rel)

                    text = safe_read(full)
                    pattern = CLASS_PATTERNS.get(sub)
                    if pattern:
                        matches = re.findall(pattern, text)
                        for m in matches:
                            subsystems[sub]["classes"].add(m)

    # Build results
    results = []

    for sub, data in subsystems.items():
        if not data["dirs"]:
            results.append({
                "subsystem": sub,
                "type": "missing_subsystem",
                "detail": "No directories found"
            })
            continue

        if not data["files"]:
            results.append({
                "subsystem": sub,
                "type": "missing_files",
                "detail": "Subsystem directories exist but contain no code files"
            })
            continue

        if not data["classes"]:
            results.append({
                "subsystem": sub,
                "type": "missing_classes",
                "detail": "Subsystem has files but no class definitions"
            })
            continue

        results.append({
            "subsystem": sub,
            "type": "complete",
            "directories": sorted(list(data["dirs"])),
            "files": sorted(list(data["files"])),
            "classes": sorted(list(data["classes"]))
        })

    return results

if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    results = run_scan()
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"[DDS-9-DEEP] Subsystem Completeness Deep Scan Complete → {OUT}")
