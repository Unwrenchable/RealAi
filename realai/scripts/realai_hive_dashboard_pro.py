import os, json, time
import matplotlib.pyplot as plt
import numpy as np

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
    world = load_json(os.path.join(recovered, "world_model.json"))
    plugins = load_json(os.path.join(root, "realai", "plugins", "registry.json"))
    heal = load_json(os.path.join(root, "logs", "last_self_heal.json"))

    folder_list = os.path.join(recovered, "REALAI_FOLDER_LIST.txt")
    folders = 0
    if os.path.exists(folder_list):
        with open(folder_list, "r", encoding="utf-8") as f:
            folders = len([line for line in f if line.strip()])

    promoted = sum(1 for v in promote.get("verify", {}).values() if v == "ok")
    skipped = sum(1 for v in promote.get("verify", {}).values() if v != "ok")
    world_keys = len(world.keys()) if isinstance(world, dict) else 0
    plugin_count = len(plugins.keys()) if isinstance(plugins, dict) else 0
    heal_rounds = heal.get("rounds", 0)

    return {
        "root": root,
        "folders": folders,
        "promoted": promoted,
        "skipped": skipped,
        "world_keys": world_keys,
        "plugins": plugin_count,
        "heal_rounds": heal_rounds
    }

# -----------------------------
# SINGLE WINDOW DASHBOARD
# -----------------------------

plt.ion()
fig, axs = plt.subplots(3, 2, figsize=(14, 10))
fig.suptitle("RealAI Hive Dashboard — Live", fontsize=16)

def update_dashboard():
    metrics = [collect_metrics(root) for root in ROOTS]
    roots = [m["root"].split("\\")[-1] for m in metrics]

    # Folders processed
    axs[0,0].clear()
    axs[0,0].bar(roots, [m["folders"] for m in metrics], color="skyblue")
    axs[0,0].set_title("Folders Processed per Root")

    # Promoted vs skipped
    axs[0,1].clear()
    axs[0,1].bar(roots, [m["promoted"] for m in metrics], color="limegreen", label="Promoted")
    axs[0,1].bar(roots, [m["skipped"] for m in metrics], bottom=[m["promoted"] for m in metrics], color="orange", label="Skipped")
    axs[0,1].set_title("Promoted vs Skipped Modules")
    axs[0,1].legend()

    # World-model keys
    axs[1,0].clear()
    axs[1,0].plot(roots, [m["world_keys"] for m in metrics], marker="o", color="purple")
    axs[1,0].set_title("World-Model Keys per Root")

    # Plugin registry
    axs[1,1].clear()
    axs[1,1].plot(roots, [m["plugins"] for m in metrics], marker="o", color="teal")
    axs[1,1].set_title("Plugin Registry Entries per Root")

    # Heatmap
    axs[2,0].clear()
    heat_data = np.array([
        [m["folders"], m["promoted"], m["world_keys"], m["plugins"]]
        for m in metrics
    ])
    axs[2,0].imshow(heat_data, cmap="hot", aspect="auto")
    axs[2,0].set_xticks(range(4))
    axs[2,0].set_xticklabels(["Folders", "Promoted", "World Keys", "Plugins"])
    axs[2,0].set_yticks(range(len(roots)))
    axs[2,0].set_yticklabels(roots)
    axs[2,0].set_title("Hive Activity Heatmap")

    # Heal rounds
    axs[2,1].clear()
    axs[2,1].bar(roots, [m["heal_rounds"] for m in metrics], color="red")
    axs[2,1].set_title("Self-Heal Rounds per Root")

    fig.canvas.draw()
    fig.canvas.flush_events()

# -----------------------------
# AUTO REFRESH LOOP
# -----------------------------

if __name__ == "__main__":
    while True:
        update_dashboard()
        time.sleep(5)
