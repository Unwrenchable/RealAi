import os, json, subprocess, shutil

# ============================================================
# RealAI Multi-Root Hive Integrator
# Runs full RealAI integration pipeline across multiple roots
# ============================================================

ROOTS = [
    r"C:\RealAI-clean",
    r"D:\models",
    r"D:\realai_archives",
    r"C:\tools\realai",
    r"C:\llama-vulkan",
    r"C:\llama.cpp",
    r"C:\Users\tsmit\backups",
    r"C:\Users\tsmit\models",
    r"C:\tmp",
    r"C:\Users\tsmit\projects\realai-clean",
    r"C:\Users\tsmit\realai"
]

SCRIPTS_DIR = r"C:\RealAI-clean\scripts"

PHASES = [
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

SKIP_SCAN_ROOT = {
    "diff_imports_promote_allowlist.py",
    "curated_promote.py",
    "world_model_merger.py",
    "plugin_registry_builder.py",
    "wire_recovered.py",
    "unified_structure_validator.py",
    "self_heal_loop.py",
    "monitor_model.py"
}

def clean_folder_list(folder_list):
    if not os.path.exists(folder_list):
        return
    with open(folder_list, "r", encoding="utf-8-sig") as f:
        lines = [line.strip() for line in f if line.strip()]
    with open(folder_list, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def merge(src, dest):
    if os.path.exists(src):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(src, dest)
        print(f"[merge] {src} → {dest}")

def run_script(script, root, folder):
    script_path = os.path.join(SCRIPTS_DIR, script)
    args = ["python", script_path]
    if script not in SKIP_SCAN_ROOT:
        args += ["--scan-root", folder]
    subprocess.run(args, check=True)
    print(f"[phase] {script} complete for {folder}")

def apply_results(root):
    recovered = os.path.join(root, "recovered")
    promote = load_json(os.path.join(recovered, "CURATED_PROMOTE_LOG.json"))
    allowlist = load_json(os.path.join(recovered, "promote_allowlist_from_imports.json"))
    world = load_json(os.path.join(recovered, "world_model.json"))

    for module, status in promote.get("verify", {}).items():
        if status == "ok":
            src = os.path.join(root, "modules", module.replace(".", os.sep) + ".py")
            dest = os.path.join(root, "realai", module.replace(".", os.sep) + ".py")
            merge(src, dest)

    for item in allowlist.get("candidates", []):
        src = item.get("path")
        if src and os.path.exists(src):
            dest = src.replace("temp_repos", "realai")
            merge(src, dest)

    world_out = os.path.join(root, "realai", "world_model.json")
    os.makedirs(os.path.dirname(world_out), exist_ok=True)
    with open(world_out, "w", encoding="utf-8") as f:
        json.dump(world, f, indent=2)

def run_root(root):
    print(f"\n=== [hive] Starting integration for root: {root} ===")

    recovered = os.path.join(root, "recovered")
    folder_list = os.path.join(recovered, "REALAI_FOLDER_LIST.txt")

    if not os.path.exists(folder_list):
        print(f"[hive] No folder list found for {root}, skipping.")
        return

    clean_folder_list(folder_list)

    with open(folder_list, "r", encoding="utf-8") as f:
        folders = [line.strip() for line in f if line.strip()]

    print(f"[hive] Loaded {len(folders)} folders for {root}")

    for folder in folders:
        for script in PHASES:
            run_script(script, root, folder)

    apply_results(root)

    print(f"=== [hive] Completed integration for root: {root} ===\n")

def main():
    print("=== RealAI Multi-Root Hive Integrator ===")
    for root in ROOTS:
        if os.path.exists(root):
            run_root(root)
        else:
            print(f"[hive] Root not found, skipping: {root}")
    print("=== Hive integration complete across all roots ===")

if __name__ == "__main__":
    main()
