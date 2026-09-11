"""
Whole-repo walker for RealAI-clean.

Walks nested folders (any depth), extracts AST signals, indexes runnable
scripts, and builds a unify map of duplicate / nested implementations.
"""

from __future__ import annotations

import ast
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

SKIP_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    "dist",
    "build",
    ".next",
    ".cache",
    "site-packages",
    "models",
    "checkpoints_lora",
    ".pnpm",
    "pnpm-store",
    "coverage",
    "Output",
    ".eggs",
    "Lib",
    "Scripts",
}

# Bulk dumps — still note as nests, but do not AST-walk every file
SKIP_SCAN_TREE_MARKERS = (
    "recovered",
    "temp_repos",
    "realai_historical_backups",
    "RealAI_Recovery_SAFE",
    "kilo_worktrees",
)

NEST_HINT_RE = re.compile(
    r"(gold|recovery|recycle|grok_export|from[-_]|cotton|HOMEPC|clean_backup|"
    r"unique-modules|agent_tools_gold|C_realai_|orchestration|hierarchical|"
    r"plugins[/\\]abilities|plugins[/\\]tools|from_desktop|nest)",
    re.I,
)

RUNNABLE_DIR_HINTS = {
    "scripts",
    "tools",
    "abilities",
    "adapters",
    "agent_tools",
    "scanners",
    "bin",
}

MAX_AST_BYTES = 1_500_000
MAX_MODULES = 12_000
MAX_JS_JSON = 8_000
MAX_JSON_BYTES = 2_000_000

JS_EXPORT_RE = re.compile(
    r"(?:export\s+(?:default\s+)?(?:async\s+)?function\s+(\w+)|"
    r"export\s+(?:const|let|var)\s+(\w+)|"
    r"(?:module\.exports|exports)\.(\w+)\s*=|"
    r"function\s+(\w+)\s*\(|"
    r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\()",
    re.M,
)
JS_REQUIRE_RE = re.compile(
    r"""(?:require\s*\(\s*['"]([^'"]+)['"]\s*\)|import\s+(?:[^;]*?\s+from\s+)?['"]([^'"]+)['"])""",
    re.M,
)


def safe_read(path: Path, limit: int = MAX_AST_BYTES) -> str:
    try:
        data = path.read_bytes()[:limit]
        return data.decode("utf-8", errors="replace")
    except OSError:
        return ""


def safe_write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def _rel(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _should_skip_dir(name: str) -> bool:
    return name in SKIP_DIR_NAMES or name.startswith(".")


def _in_skip_tree(rel: str) -> bool:
    low = rel.lower().replace("\\", "/")
    return any(m.lower() in low for m in SKIP_SCAN_TREE_MARKERS)


class RealAIRootWalker:
    """
    Recursive walker that keeps going deeper into every folder it analyzes.

      - walks root (or any start folder) to maximum nesting depth
      - for each folder: records a mini tree (subdirs + code files)
      - deepen=True: AST/signal-scan gold + imports/external nests (not bulk recovered/)
      - indexes .py / .js / .json at any level
      - ranks deepest nests for unify → organize → wire
    """

    def __init__(
        self,
        root: Path,
        out: Path,
        max_modules: int = MAX_MODULES,
        deepen: bool = False,
        start: Optional[Path] = None,
    ):
        self.root = root.resolve()
        self.out = out
        self.max_modules = max_modules
        self.deepen = bool(deepen)
        start_path = (start or self.root).resolve()
        self.start = start_path
        self.scanned_dirs: Set[str] = set()
        self.pending: List[Path] = [self.start]
        self.modules: List[Dict[str, Any]] = []
        self.nested_folders: List[Dict[str, Any]] = []
        self.folder_trees: List[Dict[str, Any]] = []
        self.runnable_scripts: List[Dict[str, Any]] = []
        self.js_files: List[Dict[str, Any]] = []
        self.json_files: List[Dict[str, Any]] = []
        self._basename_paths: Dict[str, List[str]] = defaultdict(list)
        self._scripts_by_name: Dict[str, List[str]] = defaultdict(list)
        self._js_by_name: Dict[str, List[str]] = defaultdict(list)
        self._json_by_name: Dict[str, List[str]] = defaultdict(list)
        self.max_depth_seen = 0
        self.truncated = False

    def _should_skip_ast(self, rel_folder: str) -> bool:
        """Bulk dumps stay basename-only unless deepen into gold/external nests."""
        if rel_folder in ("", "."):
            return False
        low = rel_folder.lower().replace("\\", "/")
        # Always skip true bulk archives for AST (still recurse + index names)
        if any(
            m in low
            for m in (
                "recovered/",
                "/recovered",
                "temp_repos",
                "realai_historical_backups",
                "realai_recovery_safe",
            )
        ):
            return True
        if not _in_skip_tree(rel_folder):
            return False
        if self.deepen and (
            NEST_HINT_RE.search(rel_folder)
            or "imports/external" in low
            or "/gold" in low
            or low.endswith("gold")
        ):
            return False
        return True

    def run(self) -> Dict[str, Any]:
        while self.pending:
            folder = self.pending.pop()
            try:
                key = str(folder.resolve()).lower()
            except OSError:
                continue
            if key in self.scanned_dirs or not folder.exists() or not folder.is_dir():
                continue
            self.scanned_dirs.add(key)
            self._scan_folder(folder)

        # Deepest first — these drive unify/organize
        nests_sorted = sorted(
            self.nested_folders,
            key=lambda n: (-int(n.get("depth") or 0), -int(n.get("code_top") or 0), n.get("rel") or ""),
        )
        deepest = nests_sorted[:120]
        leaf_nests = [
            n
            for n in nests_sorted
            if int(n.get("subdirs") or 0) == 0 and int(n.get("code_top") or 0) > 0
        ][:80]

        flows = self._infer_flows(self.modules)
        architecture = self._architecture(flows)
        unify = self._unify_map()
        scripts_index = {
            name: paths
            for name, paths in sorted(self._scripts_by_name.items())
            if paths
        }

        payload = {
            "version": 4,
            "root": str(self.root),
            "start": _rel(self.root, self.start) if self.start != self.root else ".",
            "deepen": self.deepen,
            "max_depth_seen": self.max_depth_seen,
            "scanned_dirs": len(self.scanned_dirs),
            "module_count": len(self.modules),
            "truncated": self.truncated,
            "nested_folders": nests_sorted[:800],
            "nested_folder_count": len(self.nested_folders),
            "deepest_nests": deepest,
            "leaf_nests": leaf_nests,
            "folder_trees": self.folder_trees[:400],
            "folder_tree_count": len(self.folder_trees),
            "runnable_scripts": self.runnable_scripts[:2000],
            "runnable_script_count": len(self.runnable_scripts),
            "scripts_by_name": scripts_index,
            "js_files": self.js_files[:1500],
            "js_file_count": len(self.js_files),
            "js_by_name": {k: v for k, v in sorted(self._js_by_name.items()) if v},
            "json_files": self.json_files[:1500],
            "json_file_count": len(self.json_files),
            "json_by_name": {k: v for k, v in sorted(self._json_by_name.items()) if v},
            "unify": unify,
            "flows": {k: v[:80] for k, v in flows.items()},
            "architecture": architecture,
            "modules_sample": self.modules[:300],
            "notes": [
                "Every analyzed folder enqueues its subfolders — walk goes deeper until leaves.",
                "deepest_nests / leaf_nests feed organize (deepest-first patch/merge).",
                "Use deepen=True to AST-scan gold + imports/external nests.",
            ],
        }
        safe_write(self.out, payload)

        md = self.out.with_suffix(".md")
        md.write_text(self._to_markdown(payload), encoding="utf-8")
        payload["map_md"] = str(md)
        return payload

    def _scan_folder(self, folder: Path) -> None:
        rel_folder = _rel(self.root, folder)
        skip_ast = self._should_skip_ast(rel_folder)
        depth = 0 if rel_folder in ("", ".") else rel_folder.count("/") + 1
        if depth > self.max_depth_seen:
            self.max_depth_seen = depth

        try:
            children = list(folder.iterdir())
        except OSError:
            return

        subdirs: List[str] = []
        code_files: List[str] = []
        py_top = js_top = json_top = 0
        for item in children:
            name = item.name
            if item.is_dir():
                if _should_skip_dir(name):
                    continue
                subdirs.append(name)
                continue
            suf = item.suffix.lower()
            if suf == ".py":
                py_top += 1
                code_files.append(name)
            elif suf in {".js", ".cjs", ".mjs"}:
                js_top += 1
                code_files.append(name)
            elif suf == ".json":
                json_top += 1
                code_files.append(name)

        code_top = py_top + js_top + json_top
        # Mini tree for every folder we enter (enables deepen/unify)
        if rel_folder not in ("", ".") or code_top or subdirs:
            self.folder_trees.append(
                {
                    "rel": rel_folder or ".",
                    "depth": depth,
                    "subdirs": subdirs[:80],
                    "subdir_count": len(subdirs),
                    "code_files": code_files[:80],
                    "py_top": py_top,
                    "js_top": js_top,
                    "json_top": json_top,
                    "code_top": code_top,
                    "skip_ast": skip_ast,
                    "nest_hint": bool(NEST_HINT_RE.search(rel_folder or "")),
                }
            )

        nest = bool(NEST_HINT_RE.search(rel_folder or ""))
        junk_leaf = any(
            x in (rel_folder or "").lower()
            for x in ("__pycache__", "pycache_source", "node_modules", ".egg-info")
        )
        if (
            rel_folder
            and rel_folder != "."
            and not junk_leaf
            and (nest or depth >= 2 or code_top > 0)
        ):
            self.nested_folders.append(
                {
                    "rel": rel_folder,
                    "depth": depth,
                    "nest_hint": nest,
                    "py_top": py_top,
                    "js_top": js_top,
                    "json_top": json_top,
                    "code_top": code_top,
                    "subdirs": len(subdirs),
                    "skip_ast": skip_ast,
                    "is_leaf": len(subdirs) == 0,
                }
            )

        for item in children:
            name = item.name
            if item.is_dir():
                if _should_skip_dir(name):
                    continue
                # Always enqueue subfolders — this is how we go deeper and deeper
                self.pending.append(item)
                continue

            suffix = item.suffix.lower()
            if suffix not in {".py", ".js", ".cjs", ".mjs", ".json"}:
                continue

            rel = _rel(self.root, item)
            self._basename_paths[item.name].append(rel)

            if suffix in {".js", ".cjs", ".mjs"}:
                self._index_js(item, rel, skip_ast=skip_ast)
                continue
            if suffix == ".json":
                self._index_json(item, rel, skip_ast=skip_ast)
                continue

            # ---- Python ----
            is_runnable = self._looks_runnable(item, rel)
            if is_runnable:
                entry = {
                    "rel": rel,
                    "name": item.name,
                    "dir": str(Path(rel).parent).replace("\\", "/"),
                    "depth": rel.count("/"),
                    "kind": "py",
                }
                self.runnable_scripts.append(entry)
                self._scripts_by_name[item.name].append(rel)

            if skip_ast:
                continue
            if len(self.modules) >= self.max_modules:
                self.truncated = True
                continue

            try:
                if item.stat().st_size > MAX_AST_BYTES:
                    continue
            except OSError:
                continue

            text = safe_read(item)
            if not text.strip():
                continue
            try:
                tree = ast.parse(text)
            except SyntaxError:
                continue

            classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
            funcs = [n.name for n in tree.body if isinstance(n, ast.FunctionDef)]
            # also nested defs lightly
            for n in ast.walk(tree):
                if isinstance(n, ast.ClassDef) and n.name not in classes:
                    classes.append(n.name)
                if isinstance(n, ast.FunctionDef) and n.name not in funcs:
                    funcs.append(n.name)

            imports: List[str] = []
            for n in ast.walk(tree):
                if isinstance(n, ast.Import):
                    for alias in n.names:
                        imports.append(alias.name)
                elif isinstance(n, ast.ImportFrom) and n.module:
                    imports.append(n.module)

            # Import-driven discovery of sibling packages under root
            for imp in imports:
                top = imp.split(".", 1)[0]
                if not top or top.startswith("_"):
                    continue
                imp_path = self.root / top
                if imp_path.is_dir():
                    key = str(imp_path.resolve()).lower()
                    if key not in self.scanned_dirs:
                        self.pending.append(imp_path)

            self.modules.append(
                {
                    "path": rel,
                    "kind": "py",
                    "classes": classes[:40],
                    "functions": funcs[:60],
                    "imports": imports[:40],
                    "runnable": is_runnable,
                }
            )

    def _index_js(self, path: Path, rel: str, skip_ast: bool = False) -> None:
        if len(self.js_files) >= MAX_JS_JSON:
            return
        self._js_by_name[path.name].append(rel)
        entry: Dict[str, Any] = {
            "rel": rel,
            "name": path.name,
            "dir": str(Path(rel).parent).replace("\\", "/"),
            "depth": rel.count("/"),
            "kind": "js",
            "nest_hint": bool(NEST_HINT_RE.search(rel)),
        }
        # runnable-ish JS under tools/scripts/apps
        top = rel.split("/", 1)[0].lower() if rel else ""
        if top in RUNNABLE_DIR_HINTS or top == "apps" or path.name.startswith("realai-"):
            self.runnable_scripts.append({**entry, "kind": "js"})
            self._scripts_by_name[path.name].append(rel)

        if skip_ast:
            self.js_files.append(entry)
            return
        try:
            if path.stat().st_size > MAX_AST_BYTES:
                self.js_files.append(entry)
                return
        except OSError:
            self.js_files.append(entry)
            return
        text = safe_read(path)
        exports: List[str] = []
        for m in JS_EXPORT_RE.finditer(text):
            for g in m.groups():
                if g and g not in exports:
                    exports.append(g)
        requires: List[str] = []
        for m in JS_REQUIRE_RE.finditer(text):
            for g in m.groups():
                if g and g not in requires:
                    requires.append(g)
        entry["exports"] = exports[:40]
        entry["requires"] = requires[:40]
        self.js_files.append(entry)

    def _index_json(self, path: Path, rel: str, skip_ast: bool = False) -> None:
        if len(self.json_files) >= MAX_JS_JSON:
            return
        self._json_by_name[path.name].append(rel)
        entry: Dict[str, Any] = {
            "rel": rel,
            "name": path.name,
            "dir": str(Path(rel).parent).replace("\\", "/"),
            "depth": rel.count("/"),
            "kind": "json",
            "nest_hint": bool(NEST_HINT_RE.search(rel)),
        }
        if skip_ast:
            self.json_files.append(entry)
            return
        try:
            sz = path.stat().st_size
            entry["bytes"] = sz
            if sz > MAX_JSON_BYTES:
                self.json_files.append(entry)
                return
        except OSError:
            self.json_files.append(entry)
            return
        text = safe_read(path, limit=MAX_JSON_BYTES)
        try:
            data = json.loads(text)
        except Exception:
            entry["parse_ok"] = False
            self.json_files.append(entry)
            return
        entry["parse_ok"] = True
        if isinstance(data, dict):
            keys = list(data.keys())[:40]
            entry["keys"] = keys
            entry["type"] = "object"
            # light classification
            low_keys = {k.lower() for k in keys}
            if "plugins" in low_keys or path.name.lower() in {"registry.json", "plugin_manifest.json"}:
                entry["role"] = "plugin_registry"
            elif "agents" in low_keys or path.name.lower().startswith("agent"):
                entry["role"] = "agents"
            elif path.name.lower() == "package.json":
                entry["role"] = "package"
                entry["pkg_name"] = data.get("name")
            elif "dependencies" in low_keys or "devDependencies" in low_keys:
                entry["role"] = "package_lockish"
            elif "items" in low_keys and "version" in low_keys:
                entry["role"] = "allowlist"
            else:
                entry["role"] = "config"
        elif isinstance(data, list):
            entry["type"] = "array"
            entry["length"] = len(data)
            entry["role"] = "list"
        else:
            entry["type"] = type(data).__name__
            entry["role"] = "scalar"
        self.json_files.append(entry)

    def _looks_runnable(self, path: Path, rel: str) -> bool:
        parts = Path(rel).parts
        if parts and parts[0].lower() in RUNNABLE_DIR_HINTS:
            return True
        if path.name in {"walk_root.py", "manage.py"}:
            return True
        # cheap text probe for __main__
        try:
            head = path.read_bytes()[:8000].decode("utf-8", errors="replace")
        except OSError:
            return False
        return 'if __name__ == "__main__"' in head or "if __name__ == '__main__'" in head

    def _unify_map(self) -> Dict[str, Any]:
        dupes = []
        for name, paths in self._basename_paths.items():
            if len(paths) < 2:
                continue
            # interesting if nests / product trees collide
            nests = [p for p in paths if NEST_HINT_RE.search(p) or p.count("/") >= 2]
            product = [
                p
                for p in paths
                if p.split("/", 1)[0]
                in {
                    "abilities",
                    "core",
                    "modules",
                    "realai",
                    "agent_tools",
                    "adapters",
                    "plugins",
                    "scripts",
                    "tools",
                }
            ]
            if len(paths) >= 2 and (nests or len(product) >= 2 or len(paths) >= 3):
                dupes.append(
                    {
                        "basename": name,
                        "count": len(paths),
                        "paths": paths[:20],
                        "product_hits": product[:10],
                        "nest_hits": nests[:10],
                    }
                )
        dupes.sort(key=lambda x: (-x["count"], x["basename"]))

        multi_scripts = {
            k: v
            for k, v in self._scripts_by_name.items()
            if len(v) > 1
        }
        return {
            "duplicate_basenames": dupes[:400],
            "duplicate_basename_count": len(dupes),
            "multi_location_scripts": dict(list(multi_scripts.items())[:200]),
            "notes": [
                "Prefer product paths (abilities/, core/, modules/, realai/, scripts/) over recovered nests.",
                "Use scripts_by_name to run a script from any nesting level via craft.",
                "deep_promote / curated_promote consume unify collisions.",
            ],
        }

    def _infer_flows(self, modules: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        flows: Dict[str, List[str]] = {
            "orchestrators": [],
            "providers": [],
            "memory": [],
            "world": [],
            "plugins": [],
            "http_orchestrators": [],
            "training": [],
            "self_heal": [],
            "agents": [],
            "runtime_bridges": [],
            "recovery": [],
            "ability_catalogs": [],
            "multi_agent": [],
            "specialists": [],
            "secure_tools": [],
            "scripts": [],
        }

        for m in modules:
            path = m["path"]
            classes = m["classes"]
            imports = m["imports"]
            funcs = m.get("functions") or []

            if any("Orchestrator" in c for c in classes) or "orchestrat" in path.lower():
                flows["orchestrators"].append(path)
            if any("Provider" in c for c in classes):
                flows["providers"].append(path)
            if any("Memory" in c for c in classes) or "memory" in path.lower():
                flows["memory"].append(path)
            if any("WorldModel" in c or "WorldState" in c for c in classes):
                flows["world"].append(path)
            if "plugin" in path.lower() or any("Plugin" in c for c in classes):
                flows["plugins"].append(path)
            if any(imp == "http.server" or imp.endswith(".http.server") for imp in imports):
                flows["http_orchestrators"].append(path)
            if any("train" in f.lower() for f in funcs) or any(
                "FineTune" in c or "Train" in c for c in classes
            ):
                flows["training"].append(path)
            if "self_heal" in path.lower() or "self_improve" in path.lower():
                flows["self_heal"].append(path)
            if "agent" in path.lower():
                flows["agents"].append(path)
            if "runtime_bridge" in path.lower():
                flows["runtime_bridges"].append(path)
            if "recovery" in path.lower() or "recovered" in path.lower():
                flows["recovery"].append(path)
            if "ability" in path.lower():
                flows["ability_catalogs"].append(path)
            if "multi_agent" in path.lower():
                flows["multi_agent"].append(path)
            if "specialist" in path.lower() or any("Specialist" in c for c in classes):
                flows["specialists"].append(path)
            if "secure_tool" in path.lower() or any("SecureTool" in c for c in classes):
                flows["secure_tools"].append(path)
            if m.get("runnable"):
                flows["scripts"].append(path)

        return flows

    def _architecture(self, flows: Dict[str, List[str]]) -> Dict[str, Any]:
        return {
            "core": {
                "orchestrators": flows["orchestrators"][:40],
                "providers": flows["providers"][:40],
                "memory": flows["memory"][:40],
                "world": flows["world"][:40],
                "plugins": flows["plugins"][:40],
                "specialists": flows["specialists"][:40],
                "secure_tools": flows["secure_tools"][:40],
            },
            "external_api": {
                "http_orchestrators": flows["http_orchestrators"][:40],
                "runtime_bridges": flows["runtime_bridges"][:40],
            },
            "training": flows["training"][:40],
            "self_heal": flows["self_heal"][:40],
            "agents": flows["agents"][:40],
            "recovery": flows["recovery"][:40],
            "ability_catalogs": flows["ability_catalogs"][:40],
            "multi_agent": flows["multi_agent"][:40],
            "runnable_scripts_sample": flows["scripts"][:60],
            "summary": (
                "Unified architecture from full nested root walk. "
                "Use unify.duplicate_basenames + scripts_by_name for craft dispatch."
            ),
        }

    def _to_markdown(self, payload: Dict[str, Any]) -> str:
        lines = [
            "# RealAI root walk — nested unify map",
            "",
            f"- root: `{payload['root']}`",
            f"- scanned_dirs: {payload['scanned_dirs']}",
            f"- modules_ast: {payload['module_count']} (truncated={payload['truncated']})",
            f"- nested_folders: {payload['nested_folder_count']}",
            f"- runnable_scripts: {payload['runnable_script_count']}",
            f"- js_files: {payload.get('js_file_count', 0)}",
            f"- json_files: {payload.get('json_file_count', 0)}",
            f"- max_depth_seen: {payload.get('max_depth_seen', 0)}",
            f"- deepen: {payload.get('deepen')}",
            f"- duplicate_basenames: {payload['unify']['duplicate_basename_count']}",
            "",
            "## Deepest nests (unify/organize first)",
        ]
        for n in (payload.get("deepest_nests") or [])[:40]:
            flag = " NEST" if n.get("nest_hint") else ""
            leaf = " LEAF" if n.get("is_leaf") else ""
            lines.append(
                f"- `{n['rel']}` depth={n['depth']} code={n.get('code_top', 0)} "
                f"subdirs={n.get('subdirs', 0)}{flag}{leaf}"
            )
        lines.append("")
        lines.append("## Nested folders (sample)")
        for n in (payload.get("nested_folders") or [])[:40]:
            flag = " NEST" if n.get("nest_hint") else ""
            lines.append(
                f"- `{n['rel']}` depth={n['depth']} code={n.get('code_top', n.get('py_top', 0))}{flag}"
            )
        lines.append("")
        lines.append("## Unify collisions (same basename, many places)")
        for d in (payload.get("unify") or {}).get("duplicate_basenames") or [][:30]:
            lines.append(f"- **{d['basename']}** ×{d['count']}")
            for p in d.get("paths") or [][:6]:
                lines.append(f"  - `{p}`")
        lines.append("")
        lines.append("## Scripts available at multiple levels")
        multi = (payload.get("unify") or {}).get("multi_location_scripts") or {}
        for name, paths in list(multi.items())[:25]:
            lines.append(f"- **{name}**")
            for p in paths[:5]:
                lines.append(f"  - `{p}`")
        lines.append("")
        lines.append("## JS samples")
        for j in (payload.get("js_files") or [])[:20]:
            ex = ",".join((j.get("exports") or [])[:5])
            lines.append(f"- `{j.get('rel')}` exports=[{ex}]")
        lines.append("")
        lines.append("## JSON samples")
        for j in (payload.get("json_files") or [])[:20]:
            role = j.get("role") or "?"
            lines.append(f"- `{j.get('rel')}` role={role}")
        lines.append("")
        lines.append("## Flows (counts)")
        for k, v in (payload.get("flows") or {}).items():
            lines.append(f"- {k}: {len(v)}")
        lines.append("")
        lines.append(
            "Craft: `/walk deepen` · `/walk <folder>` · `/unify` · `/organize apply` · "
            "`/deep-unify` · `/scripts` · `/run-script <name>` · `/dispatch all`"
        )
        return "\n".join(lines) + "\n"


def resolve_script_from_walk(
    home: Path,
    script_name: str,
    prefer: Optional[List[str]] = None,
) -> Optional[Path]:
    """Resolve a script basename using walk index, then filesystem search."""
    name = script_name.strip().replace("\\", "/")
    if not name.endswith(".py"):
        name_py = name + ".py"
    else:
        name_py = name
    base = Path(name_py).name

    prefer = prefer or [
        "scripts/",
        "tools/",
        "abilities/",
        "adapters/",
        "agent_tools/",
        "scanners/",
        "core/",
        "modules/",
        "realai/",
    ]

    walk_json = home / "scan_results" / "realai_root_walk.json"
    candidates: List[str] = []
    if walk_json.is_file():
        try:
            data = json.loads(walk_json.read_text(encoding="utf-8"))
            by = data.get("scripts_by_name") or {}
            candidates = list(by.get(base) or [])
            # also allow exact rel match
            if name in (data.get("scripts_by_name") or {}).get(base, []):
                candidates.insert(0, name)
        except Exception:
            candidates = []

    # Always try canonical locations first
    for prefix in ("scripts", "tools"):
        p = home / prefix / base
        if p.is_file():
            return p
        # nested under scripts/tools
        if (home / prefix).is_dir():
            hits = list((home / prefix).rglob(base))
            if hits:
                return hits[0]

    def rank(rel: str) -> tuple:
        low = rel.replace("\\", "/").lower()
        for i, pref in enumerate(prefer):
            if low.startswith(pref.lower()):
                return (i, low.count("/"), len(low))
        return (100, low.count("/"), len(low))

    for rel in sorted(candidates, key=rank):
        p = home / rel
        if p.is_file():
            return p

    # Fallback: search good-code style roots any depth
    search_roots = [
        home / "scripts",
        home / "tools",
        home / "abilities",
        home / "adapters",
        home / "agent_tools",
        home / "scanners",
        home / "modules",
        home / "core",
        home / "imports" / "external",
    ]
    found: List[Path] = []
    for root in search_roots:
        if not root.is_dir():
            continue
        try:
            for p in root.rglob(base):
                if p.is_file():
                    found.append(p)
                    if len(found) >= 20:
                        break
        except OSError:
            continue
        if len(found) >= 20:
            break
    if not found:
        return None
    found.sort(key=lambda p: rank(_rel(home, p)))
    return found[0]
