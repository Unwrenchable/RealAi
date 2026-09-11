import os, json, subprocess, shutil

BASE = r"C:\RealAI-clean"
RECOVERED = os.path.join(BASE, "recovered")
SCRIPTS = os.path.join(BASE, "scripts")

def deep_scan_all():
    print("[loop] Performing universal deep scan of all folders under C:\\RealAI-clean ...")
    all_paths = []
    for dirpath, dirnames, filenames in os.walk(BASE):
        for f in filenames:
            all_paths.append(os.path.join(dirpath, f))
    print(f"[loop] Deep scan complete — {len(all_paths)} files found.")
    os.makedirs(RECOVERED, exist_ok=True)
    with open(os.path.join(RECOVERED, "REALAI_DEEP_SCAN_ALL.json"), "w", encoding="utf-8") as out:
        json.dump(all_paths, out, indent=2)

def run_script(name):
    path = os.path.join(SCRIPTS, name)
    print(f"[loop] Running {name} ...")
    subprocess.run(["python", path], check=True)
    print(f"[loop] ✅ {name} complete")

def load_json(name):
    path = os.path.join(RECOVERED, name)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def merge(src, dest):
    if os.path.exists(src):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(src, dest)
        print(f"[merge] {src} → {dest}")

def apply_results():
    print("[loop] Applying all recovered data...")
    promote = load_json("CURATED_PROMOTE_LOG.json")
    allowlist = load_json("promote_allowlist_from_imports.json")
    world = load_json("world_model.json")

    for module, status in promote.get("verify", {}).items():
        if status == "ok":
            src = os.path.join(BASE, "modules", module.replace(".", os.sep) + ".py")
            dest = os.path.join(BASE, "realai", module.replace(".", os.sep) + ".py")
            merge(src, dest)

    for item in allowlist.get("candidates", []):
        src = item.get("path")
        if src and os.path.exists(src):
            dest = src.replace("temp_repos", "realai")
            merge(src, dest)

    with open(os.path.join(BASE, "realai", "world_model.json"), "w", encoding="utf-8") as f:
        json.dump(world, f, indent=2)
    print("[loop] World model integrated.")

def verify_scan():
    print("[verify] Summarizing deep scan results...")
    total_files = 0
    total_dirs = 0
    for dirpath, dirnames, filenames in os.walk(BASE):
        total_dirs += 1
        total_files += len(filenames)
    print(f"[verify] Total directories scanned: {total_dirs}")
    print(f"[verify] Total files scanned: {total_files}")
    print(f"[verify] Deep scan root: {BASE}")

def main():
    print("[loop] Starting RealAI complete deep integration loop...")
    deep_scan_all()
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
    verify_scan()
    print("[loop] ✅ RealAI complete deep‑scan unification finished successfully.")

if __name__ == "__main__":
    main()
