#!/usr/bin/env python3
import os
import json
import re
from pathlib import Path

ROOT = Path(".").resolve()

# Alternate capability-surface patterns
PATTERN_GROUPS = {
    # 1) Autonomy triggers (intent to act)
    "autonomy_triggers": [
        r"\bshould\b", r"\bmust\b", r"\bneeds to\b", r"\brequired\b",
        r"\bautomate\b", r"\bautonomous\b", r"\bself\b", r"\bauto\b",
        r"\bbackground\b", r"\bdaemon\b",
    ],

    # 2) Meta-instructions (developer notes)
    "meta_instructions": [
        r"TODO", r"FIXME", r"NOTE", r"IMPORTANT", r"CRITICAL",
        r"REFACTOR", r"MERGE", r"REWRITE", r"UPGRADE",
        r"DEPRECATED", r"LEGACY", r"REMOVE", r"REPLACE",
    ],

    # 3) Workflow hints (pipelines, flows)
    "workflow_hints": [
        r"\bflow\b", r"\bpipeline\b", r"\bprocess\b", r"\bstep\b",
        r"\bsequence\b", r"\bgraph\b", r"\bnode\b", r"\bedge\b",
        r"\btransition\b", r"\bstate machine\b",
    ],

    # 4) AI operational verbs (model behaviors)
    "ai_operations": [
        r"\binfer\b", r"\bgenerate\b", r"\bcomplete\b", r"\bembed\b",
        r"\btokenize\b", r"\bdecode\b", r"\bencode\b",
        r"\bclassify\b", r"\bscore\b", r"\brank\b",
    ],

    # 5) System-level behaviors (engine hints)
    "system_behaviors": [
        r"\bmonitor\b", r"\bwatch\b", r"\bobserve\b", r"\blog\b",
        r"\btrack\b", r"\bdetect\b", r"\bscan\b", r"\banalyze\b",
        r"\bvalidate\b", r"\bverify\b",
    ],

    # 6) Evolution scaffolding (growth logic)
    "evolution_scaffolding": [
        r"\bgrow\b", r"\bevolve\b", r"\badapt\b", r"\bmutate\b",
        r"\bexpand\b", r"\bscale\b", r"\bupgrade\b",
        r"\bimprove\b", r"\boptimize\b",
    ],

    # 7) Plugin architecture (extensibility)
    "plugin_architecture": [
        r"\bplugin\b", r"\bplugins\b", r"\bextension\b",
        r"\bextend\b", r"\bmodular\b", r"\bmodule\b",
        r"\bcomponent\b", r"\bregistry\b",
    ],

    # 8) Tooling expansion (tools RealAI could use)
    "tooling_expansion": [
        r"\btool\b", r"\btools\b", r"\butility\b", r"\bhelper\b",
        r"\bscript\b", r"\bautomation\b",
    ],

    # 9) Hidden TODOs (latent abilities)
    "latent_abilities": [
        r"future", r"later", r"eventually", r"expand", r"add support",
        r"hook", r"callback", r"placeholder", r"stub",
    ],

    # 10) Agent instructions (behavioral hints)
    "agent_instructions": [
        r"\brole\b", r"\bpersona\b", r"\bidentity\b",
        r"\bbehavior\b", r"\bpolicy\b", r"\brules\b",
        r"\bgoals\b", r"\bintent\b",
    ],

    # 11) Model hints (architecture clues)
    "model_hints": [
        r"\btransformer\b", r"\battention\b", r"\bembedding\b",
        r"\bcontext\b", r"\bsequence\b", r"\btoken\b",
    ],

    # 12) Data hints (dataset clues)
    "data_hints": [
        r"\bdata\b", r"\bdataset\b", r"\bloader\b",
        r"\bpreprocess\b", r"\bclean\b", r"\bnormalize\b",
    ],

    # 13) Benchmark hints (performance clues)
    "benchmark_hints": [
        r"\bbenchmark\b", r"\bperformance\b", r"\bmetrics\b",
        r"\bscore\b", r"\btest\b", r"\beval\b",
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

def scan_file(path: Path):
    results = []
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
                            })
                            break
    except Exception as e:
        results.append({
            "group": "error",
            "pattern": "read_error",
            "line_no": 0,
            "line": f"ERROR: {e}",
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
                    manifest["files"][str(rel)] = matches
                    for m in matches:
                        g = m["group"]
                        if g in manifest["summary"]["by_group"]:
                            manifest["summary"]["by_group"][g] += 1
                            manifest["summary"]["total_matches"] += 1

    out_json = ROOT / "realai_alt_cavity_manifest.json"
    out_txt = ROOT / "realai_alt_cavity_summary.txt"

    with out_json.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

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

if __name__ == "__main__":
    main()
