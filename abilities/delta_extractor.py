"""
RealAI Hive Ability: delta_extractor
------------------------------------
Scans _quarantine/ for improved versions of agents, abilities, modules,
tools, orchestrator surfaces, world-model logic, GPU helpers, etc.

Extracts only:
- bigger versions
- extended versions
- more complete versions
- missing files

Outputs:
- recovered/delta_candidates/<mirrored_path>
- recovered/delta_candidates/report/delta_report.json

This is Option B: detect + extract (no auto-merge).
"""

import os
import json
import ast
import shutil

ROOT = "C:\\RealAI-clean"
QUAR = os.path.join(ROOT, "_quarantine")
OUT = os.path.join(ROOT, "recovered", "delta_candidates")

def ensure_dirs():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(os.path.join(OUT, "report"), exist_ok=True)

def list_py_files(base):
    for root, _, files in os.walk(base):
        for f in files:
            if f.endswith(".py"):
                yield os.path.join(root, f)

def count_defs(path):
    try:
        tree = ast.parse(open(path, "r", encoding="utf8").read())
        funcs = sum(isinstance(n, ast.FunctionDef) for n in tree.body)
        classes = sum(isinstance(n, ast.ClassDef) for n in tree.body)
        return funcs, classes
    except Exception:
        return 0, 0

def mirror_path(quarantine_path):
    """
    Mirror the quarantine folder structure into delta_candidates.
    Example:
      _quarantine/abilities/foo.py →
      recovered/delta_candidates/abilities/foo.py
    """
    rel = os.path.relpath(quarantine_path, QUAR)
    return os.path.join(OUT, rel)

def delta_scan():
    ensure_dirs()
    report = {
        "new_files": [],
        "improved": [],
        "summary": {}
    }

    real_files = list(list_py_files(ROOT))
    quar_files = list(list_py_files(QUAR))

    real_map = {os.path.basename(f): f for f in real_files}
    quar_map = {os.path.basename(f): f for f in quar_files}

    for name, qpath in quar_map.items():
        out_path = mirror_path(qpath)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        if name not in real_map:
            shutil.copy2(qpath, out_path)
            report["new_files"].append({
                "name": name,
                "status": "missing_in_clean",
                "extracted_to": out_path
            })
            continue

        rpath = real_map[name]

        rsize = os.path.getsize(rpath)
        qsize = os.path.getsize(qpath)

        rfunc, rclass = count_defs(rpath)
        qfunc, qclass = count_defs(qpath)

        if qsize > rsize or qfunc > rfunc or qclass > rclass:
            shutil.copy2(qpath, out_path)
            report["improved"].append({
                "name": name,
                "clean_size": rsize,
                "quarantine_size": qsize,
                "clean_funcs": rfunc,
                "quarantine_funcs": qfunc,
                "clean_classes": rclass,
                "quarantine_classes": qclass,
                "status": "bigger_or_extended_version_found",
                "extracted_to": out_path
            })

    report["summary"] = {
        "new_files": len(report["new_files"]),
        "improved_files": len(report["improved"]),
        "output_dir": OUT
    }

    with open(os.path.join(OUT, "report", "delta_report.json"), "w", encoding="utf8") as f:
        json.dump(report, f, indent=2)

    return report

# RealAI ability entrypoint
def ability_entry(input=None, context=None):
    return delta_scan()
