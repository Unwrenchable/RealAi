import os
import json
import hashlib

ROOT = "."
OUT = "alt_v3_cavity_manifest.json"

# Autonomy + Safety + Governance keyword families
ALT_V3_TERMS = [
    # Autonomy / self-governance
    "autonomy", "autonomous", "self-govern", "self-governance",
    "self-regulate", "self-regulation", "self-control",
    "self-correct", "self-correction", "self-align", "self-alignment",
    "self-evaluate", "self-evaluation", "self-assess", "self-assessment",
    "self-debug", "self-diagnose", "self-diagnostic", "self-test",
    "self-check", "self-monitor", "self-supervise",

    # Safety / guardrails / constraints
    "safety", "safe", "guardrail", "guardrails",
    "constraint", "constraints", "limit", "limiter",
    "bound", "boundary", "policy", "policies",
    "rule", "rules", "filter", "gate", "gating",
    "permission", "permissions", "auth", "authorize",
    "restrict", "restriction", "restricted",

    # Watchdog / supervisor / fallback systems
    "watchdog", "monitor", "monitoring", "supervisor",
    "controller", "governor", "fallback", "failsafe",
    "recovery", "retry", "backoff", "degradation",
    "graceful", "resilience", "resilient",

    # Reflection / analysis / reasoning
    "reflection", "self-reflection", "analysis", "self-analysis",
    "critique", "self-critique", "evaluate", "evaluation",
    "reasoning", "introspection", "introspect",

    # Health / diagnostics
    "health", "healthcheck", "diagnostic", "diagnostics",
    "probe", "check", "status", "heartbeat"
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

    for term in ALT_V3_TERMS:
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
    print(f"[alt-v3-scan] Complete. Output written to {OUT}")
