#!/usr/bin/env python3
"""
dry_run_scaffold.py
Non-destructive Phase 4 dry-run scaffold.
Scans two trees, classifies files, generates per-file diffs and a global preview manifest.
No files are modified.

Usage:
  python dry_run_scaffold.py --root /workspaces/RealAi --og /workspaces/RealAi/realai_og_mess/realai --out /workspaces/RealAi/phase4_tools/plan_phase4_preview
"""
import argparse
import os
import json
import hashlib
import difflib
import datetime
from pathlib import Path

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

def sha1_of_file(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(8192)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []

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
    a_lines = read_text(path_a) if path_a and os.path.exists(path_a) else []
    b_lines = read_text(path_b) if path_b and os.path.exists(path_b) else []
    diff = difflib.unified_diff(a_lines, b_lines, fromfile=path_a or "N/A", tofile=path_b or "N/A", lineterm="")
    return "\n".join(diff)

def scan_tree(root):
    files = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            try:
                size = os.path.getsize(full)
                sha = sha1_of_file(full)
            except Exception:
                size = 0
                sha = ""
            rel = os.path.relpath(full, root)
            files[rel] = {
                "full_path": full,
                "sha1": sha,
                "size": size
            }
    return files

def find_similar_files(files_a, files_b):
    map_a = {}
    for rel, meta in files_a.items():
        map_a.setdefault(meta["sha1"], []).append(rel)
    map_b = {}
    for rel, meta in files_b.items():
        map_b.setdefault(meta["sha1"], []).append(rel)
    identical = []
    for sha, rels in map_a.items():
        if sha in map_b and sha != "":
            for ra in rels:
                for rb in map_b[sha]:
                    identical.append((ra, rb))
    return identical

def build_preview(root, og_root, outdir):
    os.makedirs(outdir, exist_ok=True)
    previews_dir = os.path.join(outdir, "previews")
    os.makedirs(previews_dir, exist_ok=True)

    files_root = scan_tree(root)
    files_og = scan_tree(og_root)

    identical_pairs = find_similar_files(files_root, files_og)

    preview = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "root": root,
        "og_root": og_root,
        "canonical_entry": CANONICAL_ENTRY,
        "actions": []
    }

    for rel, meta in sorted(files_root.items()):
        action, reason = simple_classify(rel)
        entry = {
            "path": rel,
            "source": "root",
            "action": action,
            "reason": reason,
            "sha1": meta["sha1"],
            "size": meta["size"]
        }
        preview["actions"].append(entry)

    for rel, meta in sorted(files_og.items()):
        action, reason = simple_classify(rel)
        if any(rel == pair[1] for pair in identical_pairs):
            action = "archive"
            reason = "OG duplicate (identical content)"
        else:
            if rel not in files_root:
                act, r = simple_classify(rel)
                if act == "merge":
                    action = "merge"
                    reason = "OG contains subsystem not present in root"
                else:
                    action = "archive"
                    reason = "OG artifact (archive candidate)"
        entry = {
            "path": rel,
            "source": "og",
            "action": action,
            "reason": reason,
            "sha1": meta["sha1"],
            "size": meta["size"]
        }
        preview["actions"].append(entry)

    for act in preview["actions"]:
        if act["action"] in ("merge", "rewrite"):
            rel = act["path"]
            path_root = os.path.join(root, rel) if rel in files_root else None
            path_og = os.path.join(og_root, rel) if rel in files_og else None
            diff_text = compute_diff_preview(path_root, path_og)
            safe_name = rel.replace(os.sep, "__").replace("/", "__")
            diff_file = os.path.join(previews_dir, f"{safe_name}.diff.txt")
            try:
                with open(diff_file, "w", encoding="utf-8") as f:
                    if diff_text.strip() == "":
                        f.write("# No textual diff (file may be binary or identical)\n")
                    else:
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
        f.write("\nTop risk notes:\n")
        f.write(" - Router, model_registry, providers, agents, memory actions require manual review.\n")
        f.write(" - Any 'merge' action must be inspected in previews/ before apply.\n")
        f.write("\nPreview manifest: phase4_preview.json\n")
        f.write("Per-file diffs: previews/*.diff.txt\n")

    print("Dry-run preview generated at:", outdir)
    print("Preview manifest:", manifest_path)
    print("Per-file diffs in:", previews_dir)
    return manifest_path

def main():
    parser = argparse.ArgumentParser(description="Phase 4 dry-run scaffold (non-destructive).")
    parser.add_argument("--root", required=True, help="Path to unified runtime root (e.g., /workspaces/RealAi)")
    parser.add_argument("--og", required=True, help="Path to OG runtime root (e.g., /workspaces/RealAi/realai_og_mess/realai)")
    parser.add_argument("--out", default="plan_phase4_preview", help="Output folder for preview manifest and diffs")
    args = parser.parse_args()

    if not os.path.isdir(args.root):
        print("ERROR: root path not found:", args.root); return
    if not os.path.isdir(args.og):
        print("ERROR: og path not found:", args.og); return

    build_preview(args.root, args.og, args.out)

if __name__ == "__main__":
    main()
