#!/usr/bin/env python3
"""
dry_run_scaffold.py (Windows-optimized)
Non-destructive Phase 4 dry-run scaffold.
Scans two trees, classifies files, generates per-file diffs and a global preview manifest.
No files are modified.

Usage:
  python dry_run_scaffold.py --root C:\realai --og C:\realai\realai_og_mess\realai --out C:\realai\phase4_tools\plan_phase4_preview
"""

import argparse
import os
import json
import difflib
import datetime
from pathlib import Path

# -------------------------
# WINDOWS OPTIMIZATION PATCH
# -------------------------

SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".pytest_cache",
    ".vs", ".vscode", "dist", "build", "archive"
}

SKIP_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico",
    ".exe", ".dll", ".so", ".bin", ".dat",
    ".zip", ".tar", ".gz", ".7z"
}

def safe_read(path):
    """Binary-safe text reader."""
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []

def is_binary(path):
    """Detect binary files by extension."""
    return any(path.lower().endswith(ext) for ext in SKIP_EXT)

# -------------------------
# ORIGINAL LOGIC (patched)
# -------------------------

CANONICAL_ENTRY = "realai_server.py"
KEY_PATTERNS = {
    "router": ["router", "routes", "api_server", "server"],
    "model_registry": ["model_registry", "models.yaml", "models.yml", "registries"],
    "providers": ["providers", "provider"],
    "agents": ["agents", "planner", "orchestrator", "orchestration"],
    "memory": ["memory", "world", "personas"],
    "tools": ["tools", "plugins", "skills"],
    "sdk": ["sdk", "python", "js", "javascript"],
    "cli": ["cli", "bin", "scripts/cli"],
    "fusion_ui": ["fusion-ui", "webview", "ui", "frontend"],
    "out": ["out/", "dist/", "build/"],
    "archive": ["archive/", "archived/"],
    "og": ["realai_og_mess", "realai_og"]
}
CLASS_ACTIONS = ["merge", "rewrite", "archive", "delete", "keep"]

def simple_classify(relpath):
    lp = relpath.lower()
    if os.path.basename(lp) == CANONICAL_ENTRY:
        return "keep", "Canonical server entry"
    for key, patterns in KEY_PATTERNS.items():
        for p in patterns:
            if p in lp:
                if key in ("out", "archive"):
                    return "archive", f"Generated or archive artifact ({key})"
                if key == "og":
                    return "archive", "OG runtime copy (archive candidate)"
                if key in ("sdk", "cli", "fusion_ui"):
                    return "merge", f"SDK/CLI/UI alignment candidate ({key})"
                if key in ("router", "model_registry", "providers", "agents", "memory", "tools"):
                    return "merge", f"Core runtime subsystem ({key})"
    return "keep", "No rule matched; keep by default"

def compute_diff_preview(path_a, path_b):
    if path_a and is_binary(path_a):
        return "# Binary file skipped\n"
    if path_b and is_binary(path_b):
        return "# Binary file skipped\n"
    a_lines = safe_read(path_a) if path_a else []
    b_lines = safe_read(path_b) if path_b else []
    diff = difflib.unified_diff(a_lines, b_lines, fromfile=path_a or "N/A", tofile=path_b or "N/A", lineterm="")
    return "\n".join(diff)

def scan_tree(root):
    files = {}
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip garbage dirs
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        # Skip binary files
        filenames = [f for f in filenames if not any(f.lower().endswith(ext) for ext in SKIP_EXT)]

        for fn in filenames:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            try:
                size = os.path.getsize(full)
            except Exception:
                size = 0
            files[rel] = {
                "full_path": full,
                "sha1": "",   # Skip hashing for speed
                "size": size
            }
    return files

def find_similar_files(files_a, files_b):
    # Hashing disabled → no identical detection
    return []

def build_preview(root, og_root, outdir):
    os.makedirs(outdir, exist_ok=True)
    previews_dir = os.path.join(outdir, "previews")
    os.makedirs(previews_dir, exist_ok=True)

    files_root = scan_tree(root)
    files_og = scan_tree(og_root)

    preview = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "root": root,
        "og_root": og_root,
        "canonical_entry": CANONICAL_ENTRY,
        "actions": []
    }

    # Root files
    for rel, meta in sorted(files_root.items()):
        action, reason = simple_classify(rel)
        preview["actions"].append({
            "path": rel,
            "source": "root",
            "action": action,
            "reason": reason,
            "sha1": meta["sha1"],
            "size": meta["size"]
        })

    # OG files
    for rel, meta in sorted(files_og.items()):
        action, reason = simple_classify(rel)
        if rel not in files_root:
            if action == "merge":
                reason = "OG contains subsystem not present in root"
            else:
                action = "archive"
                reason = "OG artifact (archive candidate)"
        preview["actions"].append({
            "path": rel,
            "source": "og",
            "action": action,
            "reason": reason,
            "sha1": meta["sha1"],
            "size": meta["size"]
        })

    # Diff previews
    for act in preview["actions"]:
        if act["action"] in ("merge", "rewrite"):
            rel = act["path"]
            path_root = files_root.get(rel, {}).get("full_path")
            path_og = files_og.get(rel, {}).get("full_path")
            diff_text = compute_diff_preview(path_root, path_og)
            safe_name = rel.replace(os.sep, "__").replace("/", "__")
            diff_file = os.path.join(previews_dir, f"{safe_name}.diff.txt")
            try:
                with open(diff_file, "w", encoding="utf-8") as f:
                    f.write(diff_text)
                act["diff_preview"] = os.path.relpath(diff_file, outdir)
            except Exception as e:
                act["diff_preview"] = None
                act["diff_error"] = str(e)

    manifest_path = os.path.join(outdir, "phase4_preview.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(preview, f, indent=2)

    summary_path = os.path.join(outdir, "phase4_preview_summary.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("Phase 4 Dry-Run Preview Summary\n")
        f.write("===============================\n\n")
        f.write(f"Generated at: {preview['generated_at']}\n")
        f.write(f"Root: {root}\n")
        f.write(f"OG Root: {og_root}\n\n")
        counts = {}
        for a in preview["actions"]:
            counts[a["action"]] = counts.get(a["action"], 0) + 1
        f.write("Action counts:\n")
        for k in CLASS_ACTIONS:
            f.write(f"  {k}: {counts.get(k,0)}\n")
        f.write("\nPreview manifest: phase4_preview.json\n")
        f.write("Per-file diffs: previews/*.diff.txt\n")

    print("Dry-run preview generated at:", outdir)
    print("Preview manifest:", manifest_path)
    print("Per-file diffs in:", previews_dir)
    return manifest_path

def main():
    parser = argparse.ArgumentParser(description="Phase 4 dry-run scaffold (non-destructive).")
    parser.add_argument("--root", required=True)
    parser.add_argument("--og", required=True)
    parser.add_argument("--out", default="plan_phase4_preview")
    args = parser.parse_args()

    if not os.path.isdir(args.root):
        print("ERROR: root path not found:", args.root); return
    if not os.path.isdir(args.og):
        print("ERROR: og path not found:", args.og); return

    build_preview(args.root, args.og, args.out)

if __name__ == "__main__":
    main()
