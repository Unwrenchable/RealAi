import os
import json
import hashlib

ROOT = "."
OUT = "full_spectrum_cavity_manifest.json"

FULL_TERMS = [

    # Memory systems
    "memory", "episodic", "semantic", "working memory",
    "long-term", "cache", "persist", "checkpoint",
    "snapshot", "serialize", "deserialize", "recall",
    "retrieve", "embedding store", "vector store",

    # Training / datasets / evolution
    "train", "training", "finetune", "fine-tune",
    "dataset", "data set", "samples", "evolution",
    "evolve", "mutate", "mutation", "fitness",
    "selection", "generation", "chromosome",
    "hive", "hive model", "swarm", "population",

    # Agents / multi-agent / roles
    "agent", "agents", "multi-agent", "role",
    "capability", "capabilities", "skill", "skills",
    "planner", "planning", "reasoning", "chain",
    "chain of thought", "cot", "reflection",
    "self-reflection", "analysis", "self-analysis",

    # Plugins / tools / MCP
    "plugin", "plugins", "tool", "tools",
    "mcp", "connector", "adapter", "bridge",
    "dispatch", "dispatcher", "router",
    "schema", "validate", "validation",

    # RAG / Chroma / retrieval
    "rag", "retrieval", "chroma", "vector",
    "embedding", "embeddings", "dimension",
    "encode", "encoder", "decode", "decoder",

    # Autonomy / self-maintenance
    "autonomy", "autonomous", "self-heal",
    "self-repair", "self-upgrade", "self-maintain",
    "self-optimization", "self-regulate",
    "self-govern", "self-governance",
    "self-correct", "self-align", "self-evaluate",

    # Safety / constraints
    "safety", "safe", "guardrail", "constraint",
    "limit", "limiter", "policy", "policies",
    "rule", "rules", "filter", "gate", "gating",
    "permission", "auth", "authorize",

    # World-model / simulation / environment
    "worldmodel", "simulation", "simulator",
    "environment", "state machine", "entity",
    "npc", "actor", "behavior tree", "event loop",
    "tick", "step", "frame", "update", "worldstate",
    "terrain", "map", "grid", "pathfinding",
    "navigation", "collision", "physics",

    # Runtime / server / API / UI
    "runtime", "server", "router", "endpoint",
    "request", "response", "api", "client",
    "ui", "dom", "frontend", "backend",

    # Future features / abandoned code
    "todo", "future", "planned", "prototype",
    "experimental", "deprecated", "rewrite",
    "upgrade", "refactor", "v2", "v3"
]

def hash_file(path):
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()
    except:
        return None

def scan_file(path):
    hits = []
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read().lower()
    except:
        return hits

    for term in FULL_TERMS:
        if term in text:
            hits.append({
                "term": term,
                "path": path
            })
    return hits

def walk(root):
    manifest = []
    for dirpath, dirs, files in os.walk(root):
        for file in files:
            full = os.path.join(dirpath, file)
            results = scan_file(full)
            if results:
                manifest.append({
                    "file": full,
                    "hash": hash_file(full),
                    "hits": results
                })
    return manifest

if __name__ == "__main__":
    manifest = walk(ROOT)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"[full-spectrum-scan] Complete. Output written to {OUT}")
