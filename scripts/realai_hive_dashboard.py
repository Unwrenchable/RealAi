import os, json, matplotlib.pyplot as plt

ROOTS = [
    r"C:\RealAI-clean",
    r"D:\models",
    r"D:\realai_archives",
    r"C:\tools\realai",
    r"C:\llama-vulkan",
    r"C:\llama.cpp",
    r"C:\Users\tsmit\backups",
    r"C:\Users\tsmit\models",
    r"C:\Users\tsmit\projects\realai-clean",
    r"C:\Users\tsmit\realai"
]

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def collect_metrics(root):
    recovered = os.path.join(root, "recovered")
    promote = load_json(os.path.join(recovered, "CURATED_PROMOTE_LOG.json"))
    allowlist = load_json(os.path.join(recovered, "promote_allowlist_from_imports.json"))
    world = load_json(os.path.join(recovered, "world_model.json"))
    plugins = load_json(os.path.join(root, "realai", "plugins", "registry.json"))

    folders = 0
    folder_list = os.path.join(recovered, "REALAI_FOLDER_LIST.txt")
    if os.path.exists(folder_list):
        with open(folder_list, "r", encoding="utf-8") as f:
            folders = len([line for line in f if line.strip()])

    promoted = sum(1 for v in promote.get("verify", {}).values() if v == "ok")
    skipped = sum(1 for v in promote.get("verify", {}).values() if v != "ok")
    world_keys = len(world.keys()) if isinstance(world, dict) else 0
    plugin_count = len(plugins.keys()) if isinstance(plugins, dict) else 0

    return {
        "root": root,
        "folders": folders,
        "promoted": promoted,
        "skipped": skipped,
        "world_keys": world_keys,
        "plugins": plugin_count
    }

metrics = [collect_metrics(root) for root in ROOTS]

# Visualization
fig, axs = plt.subplots(2, 2, figsize=(12, 8))
roots = [m["root"].split("\\")[-1] for m in metrics]

axs[0,0].bar(roots, [m["folders"] for m in metrics], color="skyblue")
axs[0,0].set_title("Folders Processed per Root")

axs[0,1].bar(roots, [m["promoted"] for m in metrics], color="limegreen", label="Promoted")
axs[0,1].bar(roots, [m["skipped"] for m in metrics], color="orange", bottom=[m["promoted"] for m in metrics], label="Skipped")
axs[0,1].set_title("Promoted vs Skipped Modules")
axs[0,1].legend()

axs[1,0].plot(roots, [m["world_keys"] for m in metrics], marker="o", color="purple")
axs[1,0].set_title("World-Model Keys per Root")

axs[1,1].bar(roots, [m["plugins"] for m in metrics], color="teal")
axs[1,1].set_title("Plugin Registry Entries per Root")

plt.tight_layout()
plt.show()
