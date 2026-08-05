#!/usr/bin/env python3
import os
import json
import re
from pathlib import Path
from collections import defaultdict

ROOT = Path(".").resolve()

PATTERN_GROUPS = {
    # 1) Self-maintenance / autonomy
    "self_logic": [
        r"\bself\.", r"\bself_", r"self-maintain", r"self-repair",
        r"self-update", r"self-diff", r"self-merge", r"self-check",
        r"self-evolve", r"self-rewrite", r"self-refactor",
    ],

    # 2) Memory / RAG / vector stores
    "memory": [
        r"\bmemory\b", r"MEMORY_ENGINE", r"\bstore\b", r"\brecall\b",
        r"\bforget\b", r"\bvector\b", r"\bembedding\b", r"\bembeddings\b",
        r"\bchroma\b", r"\bfaiss\b", r"\bsqlite\b", r"\brag\b",
        r"retrieval", r"retriever",
    ],

    # 3) Training / evolution / hive / swarm
    "training_evolution": [
        r"\btrain\b", r"fine-tune", r"\bfinetune\b", r"\bpipeline\b",
        r"\bdataset\b", r"\bbenchmark\b", r"\beval\b", r"\bevaluation\b",
        r"\bmetrics\b", r"\bloss\b", r"\bgradient\b", r"\bhive\b",
        r"\bswarm\b", r"\bdistributed\b", r"\breinforcement\b",
        r"\bcurriculum\b",
    ],

    # 4) Agents / roles / personas
    "agents": [
        r"\bagent\b", r"\bagents\b", r"\bplanner\b", r"\bcritic\b",
        r"\bexecutor\b", r"\borchestrator\b", r"\bgraph\b",
        r"\bpipeline\b", r"\btask\b", r"\brole\b", r"\bpersona\b",
        r"\bidentity\b",
    ],

    # 5) Tools / plugins / packages / registry
    "tools_plugins": [
        r"\btool\b", r"\btools\b", r"\bregistry\b", r"\bschema\b",
        r"\bvalidate\b", r"\bcontract\b", r"\bplugin\b", r"\bplugins\b",
        r"\bpackage\b", r"\bpackages\b", r"\bextension\b",
    ],

    # 6) Runtime / engine / server / providers
    "runtime": [
        r"\bruntime\b", r"\bengine\b", r"\bserver\b", r"\brouter\b",
        r"\bdispatch\b", r"\bconfig\b", r"\bprovider\b", r"\bproviders\b",
        r"\brouting\b", r"\bfallback\b", r"local mode",
    ],

    # 7) World / state / environment / goals
    "world_state": [
        r"\bworld\b", r"\bstate\b", r"\bgoal\b", r"\bobserve\b",
        r"\benvironment\b", r"\bsimulation\b",
    ],

    # 8) Knowledge / graphs / ontology
    "knowledge": [
        r"\bknowledge\b", r"\bgraph\b", r"\bontology\b", r"\binference\b",
        r"\bstore\b",
    ],

    # 9) Logs / history / telemetry / analytics
    "logs_history": [
        r"\blogs\b", r"\blog\b", r"\bhistory\b", r"\bevents\b",
        r"\btraces\b", r"\btelemetry\b", r"\banalytics\b",
    ],

    # 10) Docs / workflows / instructions / guides
    "docs_workflows": [
        r"\.md\b", r"\bdocs\b", r"\binstructions\b", r"\bworkflow\b",
        r"\bworkflows\b", r"\bexamples\b", r"\btutorial\b",
        r"\bguides\b", r"\bREADME\b",
    ],

    # 11) Benchmarks / tests / performance
    "benchmarks": [
        r"\bbenchmark\b", r"\btest\b", r"\btests\b", r"\beval\b",
        r"\bperformance\b", r"\bmetrics\b",
    ],

    # 12) Data pipelines / datasets / loaders
    "data_pipelines": [
        r"\bdata\b", r"\bdataset\b", r"\bdatasets\b", r"\bloader\b",
        r"\bpreprocess\b", r"\btransform\b", r"\bbatch\b",
    ],

    # 13) AI model / inference / prompts / completions
    "ai_core": [
        r"\bmodel\b", r"\bmodels\b", r"\binference\b", r"\bembedding\b",
        r"\bembeddings\b", r"\btokenizer\b", r"\bprompt\b",
        r"\bcompletion\b", r"\bgeneration\b",
    ],

    # 14) Archive / migration / versioning
    "archive_migration": [
        r"\barchive\b", r"\bextract\b", r"\bmigrate\b", r"\bversion\b",
        r"\bversions\b", r"\bmigration\b",
    ],

    # 15) Autonomous behavior / repair / upgrade / merge / diff
    "autonomous_behavior": [
        r"\brepair\b", r"\bupgrade\b", r"\brewrite\b", r"\brefactor\b",
        r"\bmerge\b", r"\bdiff\b", r"\bnormalize\b", r"\bcontract\b",
        r"\bschema\b", r"\bversion\b",
    ],
}

COMPILED = {
    group: [re.compile(p, re.IGNORECASE) for p in patterns]
    for group, patterns in PATTERN_GROUPS.items()
}

def should_skip(path: Path) -> bool:
    parts = set(path.parts)
    skip_dirs = {
        ".git", ".venv", "node_modules", "__pycache__", ".pytest_cache",
        ".vs", "dist", "build", "coverage", ".idea",
    }
    return bool(parts & skip_dirs)

def classify_region(path: Path) -> str:
    p = str(path)
    if "realai_og_mess" in p:
        return "og"
    if "archive" in p:
        return "archive"
    if "analysis-clean" in p:
        return "clean"
    if ".kilo" in p:
        return "kilo"
    return "core"

def scan_file(path: Path):
    results = []
    region = classify_region(path)
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            for lineno, line in enumerate(f, start=1):
                for group, regexes in COMPILED.items():
                    for rx in regexes:
                        if rx.search(line):
                            results.append({
                                "group": group,
                                "pattern": rx.pattern,
                                "line_no": lineno,
                                "line": line.rstrip("\n"),
                                "region": region,
                            })
                            break
    except Exception as e:
        results.append({
            "group": "error",
            "pattern": "read_error",
            "line_no": 0,
            "line": f"ERROR: {e}",
            "region": region,
        })
    return results

def main():
    manifest = {
        "root": str(ROOT),
        "files": {},
        "summary": {
            "total_matches": 0,
            "by_group": {g: 0 for g in PATTERN_GROUPS.keys()},
        },
    }

    group_files = defaultdict(dict)

    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirpath = Path(dirpath)
        if should_skip(dirpath):
            dirnames[:] = []
            continue

        for fname in filenames:
            fpath = dirpath / fname
            rel = fpath.relative_to(ROOT)

            if fpath.suffix.lower() in {
                ".py", ".ts", ".js", ".json", ".md", ".txt", ".yaml", ".yml",
                ".html", ".css",
            }:
                matches = scan_file(fpath)
                if matches:
                    rel_str = str(rel)
                    manifest["files"][rel_str] = matches
                    for m in matches:
                        g = m["group"]
                        if g in manifest["summary"]["by_group"]:
                            manifest["summary"]["by_group"][g] += 1
                            manifest["summary"]["total_matches"] += 1
                            group_files[g].setdefault(rel_str, []).append(m)

    out_json = ROOT / "realai_full_cavity_manifest.json"
    out_txt = ROOT / "realai_full_cavity_summary.txt"

    with out_json.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # per-group shards
    for g, files in group_files.items():
        shard_path = ROOT / f"realai_full_cavity_{g}.json"
        with shard_path.open("w", encoding="utf-8") as f:
            json.dump({"root": str(ROOT), "group": g, "files": files}, f, indent=2)

    lines = []
    lines.append(f"Root: {manifest['root']}")
    lines.append(f"Total matches: {manifest['summary']['total_matches']}")
    lines.append("")
    lines.append("Matches by group:")
    for g, count in sorted(manifest["summary"]["by_group"].items(),
                           key=lambda x: -x[1]):
        lines.append(f"  {g}: {count}")
    lines.append("")
    lines.append("Top files (by match count):")
    top = sorted(
        ((fname, len(matches)) for fname, matches in manifest["files"].items()),
        key=lambda x: -x[1],
    )[:50]
    for fname, count in top:
        lines.append(f"  {fname}: {count}")

    with out_txt.open("w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[OK] Wrote", out_json)
    print(f"[OK] Wrote", out_txt)
    print("[OK] Wrote per-group shards: realai_full_cavity_<group>.json")

if __name__ == "__main__":
    main()
