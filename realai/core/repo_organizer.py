"""
Organize RealAI-clean: map nested/mis-homed .py/.js/.json into proper locations.

Uses walk index (scan_results/realai_root_walk.json) when present, otherwise
walks lightly. Default is dry-run; --apply copies/merges safely
(if_missing_or_smaller / first_existing). Never deletes nests.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DEFAULT = Path(__file__).resolve().parents[1]

SKIP_DIR_NAMES = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build",
    ".next", ".cache", "site-packages", "models", "checkpoints_lora",
}

NEST_RE = re.compile(
    r"(gold|recovery|recycle|grok_export|from[-_]|unique-modules|agent_tools_gold|"
    r"C_realai_|from_desktop|nest|imports[/\\]external)",
    re.I,
)

PRODUCT_TOP = {
    "abilities", "adapters", "agent_tools", "agents", "aura", "apps", "bin",
    "config", "core", "docs", "modules", "packages", "plugins", "realai",
    "registry", "scanners", "scripts", "server", "tools", "training",
}

# basename → preferred relative dest directory (file keeps basename)
BASENAME_DEST_DIR: Dict[str, str] = {
    "device_selector.py": "realai/plugins/tools",
    "agents.json": "agents/agentx",
    "access_profiles.json": "agents/agentx",
    "registry.json": "realai/plugins",
    "plugin_manifest.json": "realai/plugins",
    "world_model.json": "realai/world_model",
    "curated_promote_allowlist.json": "scan_results",
    "GOOD_CODE_ROOTS.json": "scan_results",
    "realai_root_walk.json": "scan_results",
    "ORGANIZE_PLAN.json": "scan_results",
}

# path keyword → dest root
PATH_RULES: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r"orchestrat", re.I), "modules/orchestrators"),
    (re.compile(r"rackup|glicko|pyramid|money_audit", re.I), "abilities/rackup"),
    (re.compile(r"specialist|hierarchical_special", re.I), "abilities"),
    (re.compile(r"secure_tool|approval_store", re.I), "abilities"),
    (re.compile(r"self_heal|self_improve|deep_promote", re.I), "realai"),
    (re.compile(r"agent_tools|tool_registry|importer\.py", re.I), "agent_tools"),
    (re.compile(r"ability_catalog|auto_wire", re.I), "abilities"),
    (re.compile(r"world_model", re.I), "realai"),
    (re.compile(r"aura.?memory|memory[/\\]engine", re.I), "realai"),
    (re.compile(r"v3_orchestrator|model_catalog", re.I), "realai"),
    (re.compile(r"walk_root|root_walker|organize_repo", re.I), "tools"),
    (re.compile(r"catalog_good_code|curated_promote|deep_promote_", re.I), "scripts"),
    (re.compile(r"plugin", re.I), "plugins"),
    (re.compile(r"training|finetune|lora", re.I), "training"),
]


@dataclass
class PlanItem:
    src: str
    dest: str
    reason: str
    action: str  # copy | merge_json | skip | would_copy | would_merge
    bytes_src: int = 0
    ok: bool = True
    note: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {
            "src": self.src,
            "dest": self.dest,
            "reason": self.reason,
            "action": self.action,
            "bytes_src": self.bytes_src,
            "ok": self.ok,
            "note": self.note,
        }


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(p: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _rel(root: Path, p: Path) -> str:
    try:
        return str(p.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def propose_dest(root: Path, rel: str) -> Optional[Tuple[str, str]]:
    """Return (dest_rel, reason) or None if already properly placed / ignore."""
    rel_n = rel.replace("\\", "/")
    parts = Path(rel_n).parts
    if not parts:
        return None
    name = parts[-1]
    suffix = Path(name).suffix.lower()
    if suffix not in {".py", ".js", ".json", ".cjs", ".mjs", ".ts"}:
        return None

    top = parts[0].lower()
    # Already in a product top-level with shallow depth → leave alone unless nest hint
    in_product = top in PRODUCT_TOP
    is_nest = bool(NEST_RE.search(rel_n))
    deep = len(parts) >= 4

    # Never auto-rehome package.json / lockfiles (too easy to clobber apps)
    if name.lower() in {"package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock"}:
        return None

    # Explicit basename routing for nest / deep copies
    if name in BASENAME_DEST_DIR:
        dest_dir = BASENAME_DEST_DIR[name]
        dest = f"{dest_dir}/{name}"
        if dest.replace("\\", "/") == rel_n:
            return None
        if is_nest or not in_product or deep:
            return dest, f"basename_rule:{dest_dir}"

    # Path keyword rules for nests / mis-homed
    if is_nest or (not in_product) or (top == "imports"):
        for rx, dest_dir in PATH_RULES:
            if rx.search(rel_n) or rx.search(name):
                # keep rackup files under abilities/rackup/
                if dest_dir == "abilities/rackup" and suffix == ".py":
                    dest = f"{dest_dir}/{name}"
                elif dest_dir == "modules/orchestrators" and suffix == ".py":
                    # avoid clobbering — use descriptive name if generic
                    dest = f"{dest_dir}/{name}"
                elif dest_dir == "scripts" and suffix == ".py":
                    dest = f"scripts/{name}"
                elif dest_dir == "tools" and suffix in {".py", ".js", ".cjs"}:
                    dest = f"tools/{name}"
                elif suffix == ".json":
                    if "registry" in name.lower():
                        dest = f"realai/plugins/{name}"
                    elif "agent" in name.lower():
                        dest = f"agents/agentx/{name}"
                    else:
                        dest = f"scan_results/from_nests/{name}"
                elif suffix in {".js", ".cjs", ".mjs", ".ts"}:
                    if "frontend" in rel_n.lower() or name.startswith("realai-"):
                        dest = f"apps/frontend/scripts/{name}" if "script" in rel_n.lower() else f"tools/{name}"
                    else:
                        dest = f"tools/{name}"
                else:
                    dest = f"{dest_dir}/{name}"
                if dest.replace("\\", "/") == rel_n:
                    return None
                return dest, f"path_rule:{dest_dir}"

    # Mis-homed product file sitting only under imports/external
    if top == "imports" and suffix == ".py":
        for rx, dest_dir in PATH_RULES:
            if rx.search(name):
                return f"{dest_dir}/{name}", f"import_promote:{dest_dir}"

    return None


def merge_json_files(src: Path, dest: Path) -> str:
    """Shallow-merge object keys; prefer dest values on conflict. Returns note."""
    try:
        a = json.loads(src.read_text(encoding="utf-8"))
        b = json.loads(dest.read_text(encoding="utf-8")) if dest.is_file() else {}
    except Exception as e:
        raise ValueError(f"json parse: {e}") from e
    if not isinstance(a, dict) or not isinstance(b, dict):
        # non-objects: replace only if dest missing
        if not dest.is_file():
            dest.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            return "copied_non_object_json"
        return "skip_non_object_dest_exists"
    merged = dict(b)
    added = 0
    for k, v in a.items():
        if k not in merged:
            merged[k] = v
            added += 1
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(merged, indent=2), encoding="utf-8")
    return f"merged_keys_added={added}"


def _rel(root: Path, p: Path) -> str:
    try:
        return str(p.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(p).replace("\\", "/")


def _depth(rel: str) -> int:
    rel = (rel or "").replace("\\", "/").strip("/")
    if not rel or rel == ".":
        return 0
    return rel.count("/") + 1


def plan_from_walk(root: Path, walk: Dict[str, Any], limit: int = 500) -> List[PlanItem]:
    """Build organize plan preferring DEEPEST nest sources first."""
    items: List[PlanItem] = []
    best_for_dest: Dict[str, PlanItem] = {}

    paths: List[str] = []

    # Explicitly pull files under deepest / leaf nests first
    for nest in list(walk.get("deepest_nests") or []) + list(walk.get("leaf_nests") or []):
        nest_rel = (nest.get("rel") or "").replace("\\", "/")
        if not nest_rel:
            continue
        nest_path = root / nest_rel
        if not nest_path.is_dir():
            continue
        try:
            for p in nest_path.rglob("*"):
                if not p.is_file():
                    continue
                if p.suffix.lower() not in {".py", ".js", ".cjs", ".mjs", ".json"}:
                    continue
                if any(part in SKIP_DIR_NAMES for part in p.parts):
                    continue
                paths.append(_rel(root, p))
        except OSError:
            continue

    for d in (walk.get("unify") or {}).get("duplicate_basenames") or []:
        for p in d.get("paths") or []:
            paths.append(p)
    for s in walk.get("runnable_scripts") or []:
        paths.append(s.get("rel") or "")
    for s in walk.get("js_files") or []:
        paths.append(s.get("rel") or s if isinstance(s, str) else "")
    for s in walk.get("json_files") or []:
        paths.append(s.get("rel") or s if isinstance(s, str) else "")
    for m in walk.get("modules_sample") or []:
        paths.append(m.get("path") or "")

    # unique, then deepest-first
    seen: set[str] = set()
    uniq: List[str] = []
    for p in paths:
        p = (p or "").replace("\\", "/")
        if not p or p in seen:
            continue
        seen.add(p)
        uniq.append(p)
    uniq.sort(key=lambda r: (-_depth(r), -len(r), r))

    for rel in uniq:
        prop = propose_dest(root, rel)
        if not prop:
            continue
        dest, reason = prop
        src_p = root / rel
        if not src_p.is_file():
            continue
        # Don't organize FROM product shallow into itself via worse path
        if not NEST_RE.search(rel) and rel.split("/", 1)[0] in PRODUCT_TOP and rel.count("/") <= 2:
            if not reason.startswith("basename_rule"):
                continue

        try:
            sz = src_p.stat().st_size
        except OSError:
            sz = 0

        cand = PlanItem(
            src=rel,
            dest=dest,
            reason=f"{reason}|depth={_depth(rel)}",
            action="would_copy",
            bytes_src=sz,
        )
        prev = best_for_dest.get(dest)
        if prev is None:
            best_for_dest[dest] = cand
        else:
            # Prefer deeper source; tie-break larger file
            if _depth(rel) > _depth(prev.src) or (
                _depth(rel) == _depth(prev.src) and sz > prev.bytes_src
            ):
                best_for_dest[dest] = cand

        if len(best_for_dest) >= limit * 2:
            # soft cap while scanning
            break

    # deepest dest sources first in output
    items = sorted(
        best_for_dest.values(),
        key=lambda it: (-_depth(it.src), -it.bytes_src, it.dest),
    )
    return items[:limit]


def apply_plan(root: Path, plan: List[PlanItem], apply: bool) -> List[PlanItem]:
    out: List[PlanItem] = []
    for it in plan:
        src = root / it.src
        dest = root / it.dest
        if not src.is_file():
            it.action = "skip_missing_src"
            it.ok = False
            out.append(it)
            continue

        suffix = dest.suffix.lower()
        if dest.is_file():
            sh_s, sh_d = sha256_file(src), sha256_file(dest)
            if sh_s and sh_d and sh_s == sh_d:
                it.action = "skip_same_hash"
                it.ok = True
                out.append(it)
                continue
            if suffix == ".json":
                if not apply:
                    it.action = "would_merge"
                    out.append(it)
                    continue
                try:
                    note = merge_json_files(src, dest)
                    it.action = "merged_json"
                    it.note = note
                    it.ok = True
                except Exception as e:
                    it.action = "merge_failed"
                    it.note = str(e)
                    it.ok = False
                out.append(it)
                continue
            # code file exists: only replace if dest smaller (enrich)
            try:
                if dest.stat().st_size >= src.stat().st_size:
                    it.action = "skip_live_same_or_larger"
                    it.ok = True
                    out.append(it)
                    continue
            except OSError:
                pass
            if not apply:
                it.action = "would_copy_enrich"
                out.append(it)
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            it.action = "copied_enrich"
            it.ok = True
            out.append(it)
            continue

        # dest missing
        if not apply:
            it.action = "would_copy"
            out.append(it)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        if suffix == ".json":
            try:
                # write src as starting point
                shutil.copy2(src, dest)
                it.action = "copied_json"
                it.ok = True
            except Exception as e:
                it.action = "copy_failed"
                it.note = str(e)
                it.ok = False
        else:
            shutil.copy2(src, dest)
            it.action = "copied"
            it.ok = True
        out.append(it)
    return out


def run_organize(
    root: Optional[Path] = None,
    apply: bool = False,
    limit: int = 500,
    refresh_walk: bool = False,
) -> Dict[str, Any]:
    root = (root or ROOT_DEFAULT).resolve()
    walk_path = root / "scan_results" / "realai_root_walk.json"
    if refresh_walk or not walk_path.is_file():
        from core.realai_root_walker import RealAIRootWalker

        RealAIRootWalker(root, walk_path).run()

    walk = json.loads(walk_path.read_text(encoding="utf-8"))
    plan = plan_from_walk(root, walk, limit=limit)
    results = apply_plan(root, plan, apply=apply)

    summary = {
        "version": 1,
        "at": utc(),
        "root": str(root),
        "apply": apply,
        "planned": len(plan),
        "actions": {},
        "ok": all(r.ok for r in results) if results else True,
    }
    for r in results:
        summary["actions"][r.action] = summary["actions"].get(r.action, 0) + 1

    payload = {
        **summary,
        "results": [r.as_dict() for r in results],
        "notes": [
            "Nests are never deleted.",
            "JSON uses shallow key merge (dest wins on conflict).",
            "Code copies only if dest missing or dest is smaller.",
            "Re-run with apply=true to write.",
        ],
    }

    out_json = root / "scan_results" / "ORGANIZE_PLAN.json"
    out_md = root / "scan_results" / "ORGANIZE_PLAN.md"
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        f"# Organize plan ({'APPLY' if apply else 'DRY-RUN'})",
        "",
        f"- planned: {len(results)}",
        f"- actions: {summary['actions']}",
        "",
        "| action | src | dest | reason |",
        "|---|---|---|---|",
    ]
    for r in results[:80]:
        lines.append(f"| {r.action} | `{r.src}` | `{r.dest}` | {r.reason} |")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    payload["path"] = str(out_json)
    payload["map_md"] = str(out_md)
    payload["summary"] = (
        f"organize apply={apply} planned={len(results)} actions={summary['actions']}"
    )
    return payload
