import os, json, yaml, re

ROOT = "C:\\realai"
OUT = "C:\\realai\\scan_results\\dds6_config_mismatches.json"

CONFIG_FILES = [
    "models.yaml",
    "providers.yaml",
    "realai.toml",
    "realai.toml.example",
    "manifest.json"
]

EXTENSIONS = [".py",".js",".ts",".json",".yaml",".yml",".toml"]

def safe_read(path):
    try:
        with open(path,"r",encoding="utf-8",errors="ignore") as f:
            return f.read()
    except:
        return ""

def load_yaml(path):
    try:
        with open(path,"r",encoding="utf-8",errors="ignore") as f:
            return yaml.safe_load(f)
    except:
        return {}

def collect_all_files(root):
    found = set()
    for dp,_,files in os.walk(root):
        for f in files:
            if any(f.lower().endswith(ext) for ext in EXTENSIONS):
                rel = os.path.relpath(os.path.join(dp,f), root)
                found.add(rel.replace("\\","/").lower())
    return found

def check_models_yaml(data, all_files):
    mismatches = []
    if not isinstance(data, dict):
        return mismatches
    models = data.get("models", [])
    for m in models:
        if isinstance(m, dict):
            path = str(m.get("path","")).lower()
            if path and path not in all_files:
                mismatches.append({
                    "type": "model_path_missing",
                    "path": path
                })
    return mismatches

def check_providers_yaml(data, all_files):
    mismatches = []
    if not isinstance(data, dict):
        return mismatches

    providers = data.get("providers", [])

    for p in providers:
        # Case 1: provider is a dict
        if isinstance(p, dict):
            entry = str(p.get("entry", "")).lower()

        # Case 2: provider is a string
        elif isinstance(p, str):
            entry = p.lower()

        # Case 3: provider is something weird
        else:
            continue

        entry = entry.replace("\\", "/")

        if entry and entry not in all_files:
            mismatches.append({
                "type": "provider_entry_missing",
                "path": entry
            })

    return mismatches

def check_manifest_json(data, all_files):
    mismatches = []
    if not isinstance(data, dict):
        return mismatches
    tools = data.get("tools", [])
    for t in tools:
        if isinstance(t, dict):
            entry = str(t.get("entry","")).lower()
            entry = entry.replace("\\","/")
            if entry and entry not in all_files:
                mismatches.append({
                    "type": "tool_entry_missing",
                    "path": entry
                })
    return mismatches

def run_scan():
    all_files = collect_all_files(ROOT)
    results = []

    for cfg in CONFIG_FILES:
        full = os.path.join(ROOT, cfg)
        if not os.path.exists(full):
            results.append({
                "config": cfg,
                "error": "missing_config_file"
            })
            continue

        if cfg.endswith(".yaml") or cfg.endswith(".yml"):
            data = load_yaml(full)
            if cfg == "models.yaml":
                results.extend(check_models_yaml(data, all_files))
            if cfg == "providers.yaml":
                results.extend(check_providers_yaml(data, all_files))

        elif cfg.endswith(".json"):
            try:
                data = json.loads(safe_read(full))
            except:
                data = {}
            results.extend(check_manifest_json(data, all_files))

        elif cfg.endswith(".toml"):
            text = safe_read(full)
            paths = re.findall(r"path\s*=\s*['\"]([^'\"]+)['\"]", text)
            for p in paths:
                lp = p.lower().replace("\\","/")
                if lp not in all_files:
                    results.append({
                        "type": "toml_path_missing",
                        "path": lp
                    })

    return results

if __name__=="__main__":
    os.makedirs(os.path.dirname(OUT),exist_ok=True)
    mismatches = run_scan()
    with open(OUT,"w",encoding="utf-8") as f:
        json.dump(mismatches, f, indent=2)
    print(f"[DDS-6] Config Mismatch Scan Complete → {OUT}")
