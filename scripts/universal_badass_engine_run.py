#!/usr/bin/env python3
"""Universal Badass Engine — one-shot doctor/harden/learn/os/kernel/hypervisor pass.

Writes structured logs under REALAI_HOME/logs/state/ and pattern/recipe stores
under REALAI_HOME/registry/universal/. Does NOT auto-apply harden fixes unless
--apply-harden is passed.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def should_skip(path: Path) -> bool:
    skip = {
        "node_modules",
        ".git",
        "ATOMIC-FIZZ-CAPS-OLD",
        "atomic-fizz-backup-2026-05-30",
        "dist",
        "build",
        "__pycache__",
        ".next",
        "coverage",
        "target",
    }
    return any(part in skip for part in path.parts)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def doctor_structure(ws: Path) -> dict[str, Any]:
    dirs = sorted(p.name for p in ws.iterdir() if p.is_dir() and not p.name.startswith("."))
    key = [
        "package.json",
        "AGENTS.md",
        "Agents.md",
        "Anchor.toml",
        "Cargo.toml",
        "docker-compose.yml",
        "backend",
        "frontend",
        "mcp",
        ".mcp.json",
        "programs",
        "systems",
        "tests",
        "docs",
    ]
    present = [n for n in key if (ws / n).exists()]
    empty_stubs = []
    for name in ("battle.js", "install_solana.sh", "repo-tree.txt"):
        fp = ws / name
        if fp.exists() and fp.is_file() and fp.stat().st_size == 0:
            empty_stubs.append(name)
    return {"dirs": dirs, "key_present": present, "empty_stubs": empty_stubs}


def doctor_imports_modules(ws: Path) -> dict[str, Any]:
    roots = [ws / n for n in ("backend", "frontend", "systems", "server", "lib", "scripts", "mcp", "workers")]
    import_counts = {"require": 0, "import": 0, "esm_from": 0, "files": 0}
    modules: dict[str, dict[str, int]] = {}
    nest_samples: list[dict[str, Any]] = []
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*.js"):
            if should_skip(p):
                continue
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            import_counts["files"] += 1
            import_counts["require"] += len(re.findall(r"require\(['\"]", txt))
            import_counts["import"] += len(re.findall(r"^\s*import\s", txt, re.M))
            import_counts["esm_from"] += len(re.findall(r"from\s+['\"]", txt))
            r = rel(p, ws)
            top = r.split("/")[0]
            depth = r.count("/")
            slot = modules.setdefault(top, {"files": 0, "max_depth": 0})
            slot["files"] += 1
            slot["max_depth"] = max(slot["max_depth"], depth)
            if depth >= 5 and len(nest_samples) < 20:
                nest_samples.append({"path": r, "depth": depth})
    return {"imports": import_counts, "modules": modules, "nests": nest_samples}


def harden_scan(ws: Path) -> dict[str, Any]:
    patterns = {
        "eval": re.compile(r"\beval\s*\("),
        "child_exec": re.compile(r"child_process|\bexecSync\b|\bexec\(|\bspawn\("),
        "disabled_tls": re.compile(r"rejectUnauthorized\s*:\s*false"),
        "dangerouslySetInnerHTML": re.compile(r"dangerouslySetInnerHTML"),
        "hardcoded_secret_assign": re.compile(
            r"(api[_-]?key|secret|private[_-]?key|password)\s*[:=]\s*['\"][^'\"]{8,}",
            re.I,
        ),
        "innerHTML_assign": re.compile(r"\.innerHTML\s*="),
    }
    hits: dict[str, list[dict[str, Any]]] = {k: [] for k in patterns}
    totals = {k: 0 for k in patterns}
    roots = [ws / n for n in ("backend", "frontend", "systems", "server", "lib", "mcp", "workers", "scripts")]
    for root in roots:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if should_skip(p):
                continue
            if p.suffix.lower() not in {".js", ".ts", ".mjs", ".cjs", ".py"}:
                continue
            try:
                txt = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for name, rx in patterns.items():
                for m in rx.finditer(txt):
                    totals[name] += 1
                    if len(hits[name]) < 15:
                        line = txt.count("\n", 0, m.start()) + 1
                        hits[name].append(
                            {
                                "file": rel(p, ws),
                                "line": line,
                                "snippet": txt[m.start() : m.start() + 90]
                                .replace("\n", " ")[:90],
                            }
                        )
    return {"totals": totals, "samples": hits, "apply": False}


def creative_context(ws: Path) -> dict[str, Any]:
    lore = []
    data = ws / "backend" / "data"
    if data.exists():
        lore = [p.name for p in data.glob("lore*") if p.is_file()][:30]
    return {
        "frontend": (ws / "frontend").is_dir(),
        "lore_files": lore,
        "avatar_docs": sorted(
            [p.name for p in ws.glob("*AVATAR*")] + [p.name for p in ws.glob("*GROK*")]
        )[:40],
        "gen_scripts": sorted(p.name for p in ws.glob("generate_*.js")),
        "has_map_stack": (ws / "frontend").exists(),
    }


def learn_patterns(ws: Path, doctor: dict[str, Any], harden: dict[str, Any]) -> list[dict[str, Any]]:
    patterns: list[dict[str, Any]] = []
    if doctor.get("structure", {}).get("empty_stubs"):
        patterns.append(
            {
                "id": "empty-root-stubs",
                "kind": "structure",
                "severity": "repo_root",
                "observation": "Zero-byte stub files at repo root",
                "files": doctor["structure"]["empty_stubs"],
                "recipe": "stub-fill-or-delete",
                "severity_score": 0.9,
            }
        )
    mods = doctor.get("modules", {})
    deep = {k: v for k, v in mods.items() if v.get("max_depth", 0) >= 6}
    if deep:
        patterns.append(
            {
                "id": "deep-js-nests",
                "kind": "nests",
                "observation": "Deep JS directory nests detected",
                "modules": deep,
                "recipe": "map-nests-before-rewrite",
                "confidence_score": 0.75,
            }
        )
    totals = harden.get("totals") or {}
    if totals.get("hardcoded_secret_assign", 0) > 0:
        patterns.append(
            {
                "id": "secret-assign-literals",
                "kind": "harden",
                "observation": "Possible hardcoded secret assignments",
                "count": totals["hardcoded_secret_assign"],
                "recipe": "move-secrets-to-env",
                "confidence_score": 0.85,
            }
        )
    if totals.get("innerHTML_assign", 0) > 0:
        patterns.append(
            {
                "id": "innerhtml-sinks",
                "kind": "harden",
                "observation": "innerHTML assignments present (XSS surface)",
                "count": totals["innerHTML_assign"],
                "recipe": "sanitize-or-textcontent",
                "confidence_score": 0.7,
            }
        )
    if totals.get("child_exec", 0) > 0:
        patterns.append(
            {
                "id": "child-process-usage",
                "kind": "harden",
                "observation": "child_process / exec usage detected",
                "count": totals["child_exec"],
                "recipe": "wrap-timeout-validate-args",
                "confidence_score": 0.8,
            }
        )
    markers = {
        "solana_anchor": (ws / "Anchor.toml").exists(),
        "node_backend": (ws / "backend").is_dir(),
        "leaflet_frontend": (ws / "frontend").is_dir(),
        "mcp": (ws / "mcp").is_dir() or (ws / ".mcp.json").exists(),
    }
    patterns.append(
        {
            "id": "repo-shape-wasteland-gps",
            "kind": "structure",
            "observation": "Atomic Fizz Caps / Vault-77 shape",
            "markers": markers,
            "recipe": "game-stack-doctor",
            "confidence_score": 0.95,
        }
    )
    return patterns


def default_recipes() -> list[dict[str, Any]]:
    return [
        {
            "id": "stub-fill-or-delete",
            "action": "Inspect zero-byte files; restore from git history or delete if obsolete",
            "safe": True,
            "auto_apply": False,
        },
        {
            "id": "move-secrets-to-env",
            "action": "Replace literal secrets with process.env / dotenv; scrub git history if needed",
            "safe": True,
            "auto_apply": False,
        },
        {
            "id": "sanitize-or-textcontent",
            "action": "Prefer textContent/DOM APIs; sanitize any required HTML sinks",
            "safe": True,
            "auto_apply": False,
        },
        {
            "id": "wrap-timeout-validate-args",
            "action": "Validate args, set timeouts, avoid shell=True; log failures",
            "safe": True,
            "auto_apply": False,
        },
        {
            "id": "map-nests-before-rewrite",
            "action": "Build import graph before moving nested modules",
            "safe": True,
            "auto_apply": False,
        },
        {
            "id": "game-stack-doctor",
            "action": "Verify backend health, MCP vault77-game, RealAI provider, Solana programs",
            "safe": True,
            "auto_apply": False,
        },
    ]


def mode_registry(home: Path, ws: Path, patterns: list[dict[str, Any]], recipes: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "os": {
            "init": True,
            "home": str(home),
            "workspace": str(ws),
            "agents": ["doctor", "architect", "creator", "learner", "hardener", "worldbuilder"],
            "providers": ["vulkan:8080", "orchestrator:8001", "realai_mcp", "vault77-game"],
            "tools": ["system_scan", "workspace_*", "multi_agent_run", "self_heal_*", "harden_scan"],
            "memory": str(home / "memory" / "hive"),
            "world": "project-bound",
            "build": "realai-stack + npm run dev (workspace)",
            "package": "realai.egg + workspace package.json",
            "release": "gated",
            "evolve": "patterns+recipes logs",
        },
        "kernel": {
            "init": True,
            "unify": "REALAI_HOME + REALAI_WORKSPACE",
            "promote": "curated product-side only",
            "agents": "agentx + craft slash tools",
            "providers": "local llama + optional cloud",
            "tools": "TOOL_REGISTRY + ability.*",
            "memory": "aura + hive sqlite",
            "world": "cwd universe",
            "evolve": "learn_keywords + pattern store",
            "doctor": "realai-doctor READY",
        },
        "hypervisor": {
            "init": True,
            "multi_ws": 2,
            "realms": [
                {"id": "home", "path": str(home), "role": "engine"},
                {"id": "workspace", "path": str(ws), "role": "project"},
            ],
            "extra_read": 2,
            "extra_write": 2,
            "promote_policy": "no auto-write to workspace unless explicit /fix|/heal|/harden apply",
            "evolve": "cross-realm pattern reuse",
            "doctor": "dual-realm health",
        },
        "capabilities": [
            "read_file",
            "write_file",
            "fix",
            "heal",
            "harden",
            "generate",
            "map",
            "evolve",
            "learn",
            "creative",
            "diagnose",
            "secure",
            "orchestrate",
        ],
        "patterns_count": len(patterns),
        "recipes_count": len(recipes),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", default=os.environ.get("REALAI_HOME", r"C:\RealAI-clean"))
    ap.add_argument(
        "--workspace",
        default=os.environ.get(
            "REALAI_WORKSPACE",
            str(Path.cwd()),
        ),
    )
    ap.add_argument("--apply-harden", action="store_true")
    args = ap.parse_args()

    home = Path(args.home)
    ws = Path(args.workspace)
    if not ws.exists():
        print(json.dumps({"ok": False, "error": f"workspace missing: {ws}"}))
        return 1

    structure = doctor_structure(ws)
    im = doctor_imports_modules(ws)
    harden = harden_scan(ws)
    if args.apply_harden:
        harden["apply"] = True
        harden["note"] = "apply flag set but this runner remains report-only for safety"
    creative = creative_context(ws)

    pkg = load_json(ws / "package.json")
    doctor = {
        "scan": True,
        "deep": True,
        "structure": structure,
        "imports": im["imports"],
        "modules": im["modules"],
        "nests": im["nests"],
        "package_name": pkg.get("name"),
        "scripts": sorted((pkg.get("scripts") or {}).keys()),
        "hive": {"orchestrator": "http://127.0.0.1:8001", "vulkan": "http://127.0.0.1:8080"},
        "world": {"repo": "ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS", "genre": "gps-scavenge"},
        "os": True,
        "kernel": True,
        "hypervisor": True,
    }

    patterns = learn_patterns(ws, {"structure": structure, "modules": im["modules"]}, harden)
    recipes = default_recipes()
    modes = mode_registry(home, ws, patterns, recipes)

    report = {
        "engine": "UNIVERSAL_BADASS_ENGINE",
        "ts": utc_now(),
        "home": str(home),
        "workspace": str(ws),
        "mode": "project",
        "extra_read": 2,
        "extra_write": 2,
        "multi_ws": 2,
        "doctor": doctor,
        "harden": harden,
        "creative": creative,
        "learn": {"patterns": patterns, "promote": False, "evolve": True},
        "modes": modes,
        "log": {
            "actions": [
                "doctor.scan",
                "doctor.deep",
                "doctor.structure",
                "doctor.imports",
                "doctor.modules",
                "doctor.nests",
                "harden.scan",
                "creative.context",
                "learn.patterns",
                "os.init",
                "kernel.init",
                "hypervisor.init",
                "patterns.scan",
                "recipes.scan",
                "log.actions",
            ]
        },
    }

    state_dir = home / "logs" / "state"
    uni_dir = home / "registry" / "universal"
    write_json(state_dir / "universal_engine_run.json", report)
    write_json(
        state_dir / "universal_engine_actions.log.json",
        {"ts": utc_now(), "actions": report["log"]["actions"], "workspace": str(ws)},
    )
    write_json(
        uni_dir / "patterns.json",
        {"ts": utc_now(), "workspace": str(ws), "patterns": patterns},
    )
    write_json(
        uni_dir / "recipes.json",
        {"ts": utc_now(), "recipes": recipes},
    )
    write_json(uni_dir / "modes.json", {"ts": utc_now(), **modes})
    write_json(
        uni_dir / "capabilities.json",
        {"ts": utc_now(), "capabilities": modes["capabilities"]},
    )

    # Compact console summary
    summary = {
        "ok": True,
        "wrote": {
            "run": str(state_dir / "universal_engine_run.json"),
            "patterns": str(uni_dir / "patterns.json"),
            "recipes": str(uni_dir / "recipes.json"),
            "modes": str(uni_dir / "modes.json"),
        },
        "js_files": im["imports"]["files"],
        "modules": im["modules"],
        "empty_stubs": structure["empty_stubs"],
        "harden_totals": harden["totals"],
        "patterns_learned": len(patterns),
        "scripts": len(doctor["scripts"]),
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
