import os, json, subprocess

BASE = r"C:\RealAI-clean"
RECOVERED = os.path.join(BASE, "recovered")
SCRIPTS = os.path.join(BASE, "scripts")

def run_script(name):
    path = os.path.join(SCRIPTS, name)
    print(f"[loop] Running {name}...")
    subprocess.run(["python", path, "--deep", "--include-hidden"], check=True)
    print(f"[loop] ✅ {name} complete")

def load_json(name):
    path = os.path.join(RECOVERED, name)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def apply_results():
    print("[loop] Applying all recovered data...")
    scan = load_json("REALAI_REPO_SCAN.json")
    promote = load_json("CURATED_PROMOTE_LOG.json")
    allowlist = load_json("promote_allowlist_from_imports.json")
    world = load_json("world_model.json")

    # Example: merge promoted modules
    for module, status in promote.get("log", {}).items():
        if status == "ok":
            src = os.path.join(BASE, "modules", module)
            dest = os.path.join(BASE, "realai", module)
            if os.path.exists(src):
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                subprocess.run(["copy", src, dest], shell=True)
                print(f"[merge] {src} → {dest}")

    # Integrate world model
    with open(os.path.join(BASE, "realai", "world_model.json"), "w", encoding="utf-8") as f:
        json.dump(world, f, indent=2)
    print("[loop] World model integrated.")

def main():
    print("[loop] Starting full RealAI integration loop...")
    phases = [
        "scan_repos_for_realai.py",
        "find_self_improve_and_lost.py",
        "promote_unified_realai.py",
        "diff_imports_promote_allowlist.py",
        "curated_promote.py",
        "world_model_merger.py",
        "plugin_registry_builder.py",
        "wire_recovered.py",
        "unified_structure_validator.py",
        "self_heal_loop.py",
        "monitor_model.py"
    ]
    for script in phases:
        run_script(script)
    apply_results()
    print("[loop] ✅ RealAI unified and complete.")

if __name__ == "__main__":
    main()
