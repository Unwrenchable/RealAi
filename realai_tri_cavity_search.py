import os
import json
import hashlib

ROOT = "."
OUT = "tri_cavity_manifest.json"

# Concept clusters (semantic families)
CONCEPT_CLUSTERS = {
    "architecture": [
        "blueprint", "design", "schema", "layout", "structure",
        "pipeline", "flow", "routing", "orchestration", "controller"
    ],
    "future_features": [
        "planned", "upcoming", "prototype", "experimental",
        "deprecated", "rewrite", "phase", "upgrade", "refactor"
    ],
    "intelligence": [
        "agent", "memory", "reasoning", "planner", "embedding",
        "semantic", "context", "intent", "capability"
    ],
    "world_model": [
        "environment", "world", "state", "simulation",
        "entity", "npc", "behavior", "action", "event"
    ],
    "integration": [
        "bridge", "adapter", "connector", "sync", "merge",
        "mapping", "translation", "compatibility"
    ]
}

def hash_file(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except:
        return None

def scan_file(path):
    results = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read().lower()
    except:
        return results

    for cluster_name, keywords in CONCEPT_CLUSTERS.items():
        for kw in keywords:
            if kw in text:
                results.append({
                    "cluster": cluster_name,
                    "keyword": kw,
                    "path": path,
                })
    return results

def walk(root):
    manifest = []
    for dirpath, dirs, files in os.walk(root):
        for file in files:
            full = os.path.join(dirpath, file)
            hits = scan_file(full)
            if hits:
                manifest.append({
                    "file": full,
                    "hash": hash_file(full),
                    "hits": hits
                })
    return manifest

if __name__ == "__main__":
    manifest = walk(ROOT)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"[tri-scan] Complete. Output written to {OUT}")
