import json, os, shutil

BASE = r"C:\RealAI-clean"
RECOVERED = os.path.join(BASE, "recovered")

def load_json(name):
    path = os.path.join(RECOVERED, name)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def merge_files(source_map):
    for src, dest in source_map.items():
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(src, dest)
            print(f"[merge] {src} → {dest}")

def main():
    print("[apply] Loading recovery data...")
    scan = load_json("REALAI_REPO_SCAN.json")
    promote = load_json("CURATED_PROMOTE_LOG.json")
    allowlist = load_json("promote_allowlist_from_imports.json")

    print("[apply] Merging promoted modules...")
    for module, status in promote.get("log", {}).items():
        if status == "ok":
            src = os.path.join(BASE, "modules", module)
            dest = os.path.join(BASE, "realai", module)
            merge_files({src: dest})

    print("[apply] Integrating allowlist imports...")
    for item in allowlist.get("candidates", []):
        src = item.get("path")
        dest = src.replace("temp_repos", "realai")
        merge_files({src: dest})

    print("[apply] Validating unified structure...")
    os.system(f"python {BASE}\\scripts\\unified_structure_validator.py")

    print("[apply] Running self-heal loop...")
    os.system(f"python {BASE}\\scripts\\self_heal_loop.py")

    print("[apply] RealAI unification complete.")

if __name__ == "__main__":
    main()
