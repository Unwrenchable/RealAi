import os
import json
import hashlib

ROOT = "."
OUT = "alt_v2_cavity_manifest.json"

# Behavioral / autonomy-focused signals
BEHAVIOR_TERMS = [
    "autonomy", "self-heal", "self-healing", "self-upgrade", "self-maintain",
    "self-maintenance", "self-optimize", "self-optimization",
    "watchdog", "supervisor", "monitor", "heartbeat",
    "fallback", "failsafe", "recovery", "retry", "backoff",
    "degradation", "graceful", "resilience", "resilient",
    "adaptive", "adaptation", "dynamic", "reactive",
    "agent loop", "control loop", "feedback", "feedback loop",
    "scheduler", "orchestrator", "controller", "governor",
    "escalation", "alert", "signal", "trigger",
    "self-test", "diagnostic", "health check", "healthcheck",
    "reconfigure", "reconfiguration", "hot-swap", "hot swap"
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

    for term in BEHAVIOR_TERMS:
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
    print(f"[alt-v2-scan] Complete. Output written to {OUT}")
