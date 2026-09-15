"""Extract languages, frameworks, README, API routes, plugin folders, keywords."""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from realai.learn.skip import should_skip_dir
from realai.learn.source import git_show_file

LANG_BY_EXT = {
    ".py": "python",
    ".pyi": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".rs": "rust",
    ".go": "go",
    ".rb": "ruby",
    ".php": "php",
    ".java": "java",
    ".kt": "kotlin",
    ".cs": "csharp",
    ".swift": "swift",
    ".scala": "scala",
    ".c": "c",
    ".h": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".m": "objc",
    ".mm": "objc",
    ".vue": "vue",
    ".svelte": "svelte",
    ".sql": "sql",
    ".sh": "shell",
    ".ps1": "powershell",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".md": "markdown",
    ".html": "html",
    ".css": "css",
    ".scss": "css",
}

FRAMEWORK_MARKERS: list[tuple[str, str]] = [
    ("package.json", "node"),
    ("pnpm-lock.yaml", "pnpm"),
    ("yarn.lock", "yarn"),
    ("nest-cli.json", "nestjs"),
    ("next.config.js", "nextjs"),
    ("next.config.mjs", "nextjs"),
    ("next.config.ts", "nextjs"),
    ("nuxt.config.ts", "nuxt"),
    ("prisma/schema.prisma", "prisma"),
    ("Cargo.toml", "rust"),
    ("go.mod", "go"),
    ("pyproject.toml", "python"),
    ("requirements.txt", "python"),
    ("Pipfile", "python"),
    ("manage.py", "django"),
    ("Gemfile", "ruby"),
    ("composer.json", "php"),
    ("pom.xml", "java"),
    ("build.gradle", "gradle"),
    ("CMakeLists.txt", "cmake"),
    ("Dockerfile", "docker"),
    ("docker-compose.yml", "docker"),
    ("vite.config.ts", "vite"),
    ("vite.config.js", "vite"),
    ("tsconfig.json", "typescript"),
    ("Rackfile", "rack"),
]

PLUGIN_DIR_NAMES = frozenset(
    {
        "plugins",
        "abilities",
        "adapters",
        "extensions",
        "addons",
        "hooks",
        "modules",
        "packages",
        "skills",
        "agents",
    }
)

STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "from",
        "this",
        "that",
        "into",
        "your",
        "you",
        "are",
        "was",
        "were",
        "have",
        "has",
        "not",
        "but",
        "use",
        "using",
        "used",
        "will",
        "can",
        "all",
        "any",
        "our",
        "its",
        "via",
        "per",
        "readme",
        "todo",
        "http",
        "https",
        "www",
        "com",
        "org",
        "file",
        "files",
        "code",
        "src",
        "lib",
        "app",
        "apps",
        "test",
        "tests",
        "spec",
        "docs",
        "doc",
        "true",
        "false",
        "null",
        "undefined",
        "export",
        "import",
        "const",
        "function",
        "class",
        "return",
        "default",
    }
)

_ROUTE_RES = [
    re.compile(r"""@(?:app|router)\.(get|post|put|patch|delete|head|options)\(\s*['\"]([^'\"]+)['\"]""", re.I),
    re.compile(r"""\b(?:app|router)\.(get|post|put|patch|delete)\(\s*['\"]([^'\"]+)['\"]""", re.I),
    re.compile(r"""createFileRoute\(\s*['\"]([^'\"]+)['\"]"""),
    re.compile(r"""@(?:Get|Post|Put|Patch|Delete|Controller)\(\s*['\"]([^'\"]+)['\"]"""),
    re.compile(r"""path\s*[:=]\s*['\"](/v\d+/[^'\"]+)['\"]"""),
    re.compile(r"""['\"](/(?:v\d+|api)/[A-Za-z0-9_./{}:-]+)['\"]"""),
]

_TEXT_EXTS = {".md", ".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".rb", ".java", ".kt", ".yml", ".yaml", ".toml", ".json"}


def detect_frameworks(root: Path) -> list[str]:
    found: list[str] = []
    for rel, label in FRAMEWORK_MARKERS:
        if (root / rel).exists() and label not in found:
            found.append(label)
    if (root / "rackup-backend").is_dir() or (root / "rackup-web").is_dir():
        if "rackup" not in found:
            found.append("rackup")
        if "nestjs" not in found and (root / "rackup-backend").is_dir():
            found.append("nestjs")
    pkg = root / "package.json"
    if pkg.is_file():
        try:
            text = pkg.read_text(encoding="utf-8", errors="replace")[:8000].lower()
        except OSError:
            text = ""
        for token, label in (
            ("\"next\"", "nextjs"),
            ("\"@nestjs/", "nestjs"),
            ("\"express\"", "express"),
            ("\"fastify\"", "fastify"),
            ("\"react\"", "react"),
            ("\"vue\"", "vue"),
            ("\"svelte\"", "svelte"),
            ("\"@tanstack/start\"", "tanstack-start"),
        ):
            if token in text and label not in found:
                found.append(label)
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            text = pyproject.read_text(encoding="utf-8", errors="replace")[:8000].lower()
        except OSError:
            text = ""
        for token, label in (
            ("fastapi", "fastapi"),
            ("flask", "flask"),
            ("django", "django"),
            ("litestar", "litestar"),
        ):
            if token in text and label not in found:
                found.append(label)
    return found


def languages_from_fingerprints(fingerprints: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for fp in fingerprints:
        ext = str(fp.get("ext") or "").lower()
        lang = LANG_BY_EXT.get(ext)
        if lang:
            counts[lang] += 1
    return dict(counts.most_common())


def read_readme(root: Path, *, limit: int = 2500) -> str:
    for name in ("README.md", "README.rst", "README.txt", "README"):
        p = root / name
        if p.is_file():
            try:
                return p.read_text(encoding="utf-8", errors="replace")[:limit]
            except OSError:
                continue
    return ""


def plugin_like_folders(root: Path, *, limit: int = 24) -> list[str]:
    out: list[str] = []
    root = root.resolve()
    try:
        for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
            if not child.is_dir() or should_skip_dir(child.name):
                continue
            if child.name.lower() in PLUGIN_DIR_NAMES:
                out.append(child.name)
            if len(out) >= limit:
                break
        # one level of nested plugin dirs (e.g. realai/plugins)
        if len(out) < limit:
            for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
                if not child.is_dir() or should_skip_dir(child.name):
                    continue
                try:
                    for nested in sorted(child.iterdir(), key=lambda p: p.name.lower()):
                        if nested.is_dir() and nested.name.lower() in PLUGIN_DIR_NAMES:
                            rel = f"{child.name}/{nested.name}"
                            if rel not in out:
                                out.append(rel)
                            if len(out) >= limit:
                                return out
                except OSError:
                    continue
    except OSError:
        return out
    return out


def _read_text_sample(root: Path, rel: str, *, limit: int = 4000, ref: str | None = None) -> str:
    p = root / rel
    try:
        if p.suffix.lower() not in _TEXT_EXTS:
            return ""
        if p.is_file():
            return p.read_text(encoding="utf-8", errors="replace")[:limit]
    except OSError:
        pass
    if ref:
        ext = Path(rel).suffix.lower()
        if ext not in _TEXT_EXTS:
            return ""
        return git_show_file(root, ref, rel, limit=limit)
    return ""


def extract_api_routes(root: Path, fingerprints: list[dict[str, Any]], *, limit: int = 40) -> list[str]:
    routes: list[str] = []
    seen: set[str] = set()
    candidates: list[tuple[str, str | None]] = []
    for fp in fingerprints:
        rel = str(fp.get("path") or "")
        if not rel.lower().endswith((".py", ".ts", ".js", ".tsx", ".jsx", ".go")):
            continue
        if any(
            tok in rel.lower()
            for tok in ("route", "api", "controller", "server", "http", "router")
        ):
            branches = fp.get("seen_on_branches") or []
            ref = branches[0] if isinstance(branches, list) and branches else None
            candidates.append((rel, ref if isinstance(ref, str) else None))
    if not candidates:
        for fp in fingerprints:
            if str(fp.get("ext") or "") not in {".py", ".ts", ".js"}:
                continue
            rel = str(fp.get("path") or "")
            branches = fp.get("seen_on_branches") or []
            ref = branches[0] if isinstance(branches, list) and branches else None
            candidates.append((rel, ref if isinstance(ref, str) else None))
            if len(candidates) >= 40:
                break
    for rel, ref in candidates[:80]:
        text = _read_text_sample(root, rel, ref=ref)
        if not text:
            continue
        for cre in _ROUTE_RES:
            for m in cre.finditer(text):
                path = m.group(m.lastindex or 1)
                if not path.startswith("/"):
                    path = "/" + path
                if path in seen or len(path) > 80:
                    continue
                seen.add(path)
                routes.append(path)
                if len(routes) >= limit:
                    return routes
    return routes


def domain_keywords(readme: str, fingerprints: list[dict[str, Any]], *, limit: int = 24) -> list[str]:
    blob = readme.lower() + "\n" + " ".join(str(fp.get("path") or "") for fp in fingerprints[:200])
    tokens = re.findall(r"[a-z][a-z0-9_]{3,}", blob.lower())
    counts: Counter[str] = Counter()
    for tok in tokens:
        if tok in STOPWORDS:
            continue
        counts[tok] += 1
    # Prefer domain-ish words that appear in paths + readme
    ranked = [w for w, _n in counts.most_common(80)]
    return ranked[:limit]


def propose_abilities(
    *,
    frameworks: list[str],
    routes: list[str],
    plugin_folders: list[str],
    keywords: list[str],
) -> list[dict[str, str]]:
    """Stub ability ids derived from signals. Always includes health."""
    proposed: list[dict[str, str]] = [
        {
            "id": "health",
            "description": "Stub liveness / contract discovery (no runtime heal)",
        }
    ]
    seen = {"health"}

    def add(aid: str, desc: str) -> None:
        key = re.sub(r"[^a-z0-9_]+", "_", aid.lower()).strip("_")
        if not key or key in seen or len(key) > 40:
            return
        seen.add(key)
        proposed.append({"id": key, "description": desc})

    add("repo_map", "Summarize learned tree layout and stack")
    for fw in frameworks:
        add(f"{fw}_context", f"Placeholder context hints for {fw} (product owns runtime)")
    for folder in plugin_folders[:6]:
        leaf = folder.replace("\\", "/").split("/")[-1]
        add(f"{leaf}_bridge", f"Bridge stub for existing {folder}/ surface")
    for route in routes[:8]:
        leaf = re.sub(r"[^a-z0-9]+", "_", route.strip("/").lower()).strip("_")
        if leaf:
            add(f"route_{leaf[:28]}", f"Hint stub for discovered route {route}")
    interesting = [
        k
        for k in keywords
        if k
        in {
            "coach",
            "rating",
            "ledger",
            "quest",
            "npc",
            "overseer",
            "caps",
            "vault",
            "sotd",
            "matchmaking",
            "tournament",
            "plugin",
            "orchestrator",
            "hive",
        }
        or k.endswith("_coach")
    ]
    for k in interesting[:8]:
        add(k if k != "plugin" else "plugin_inventory", f"Domain stub from source keyword '{k}'")
    return proposed[:16]


def extract_signals(root: Path, fingerprints: list[dict[str, Any]]) -> dict[str, Any]:
    readme = read_readme(root)
    frameworks = detect_frameworks(root)
    langs = languages_from_fingerprints(fingerprints)
    folders = plugin_like_folders(root)
    routes = extract_api_routes(root, fingerprints)
    keywords = domain_keywords(readme, fingerprints)
    abilities = propose_abilities(
        frameworks=frameworks,
        routes=routes,
        plugin_folders=folders,
        keywords=keywords,
    )
    title = ""
    for line in readme.splitlines():
        s = line.strip().lstrip("#").strip()
        if s:
            title = s[:120]
            break
    if not title:
        title = root.name
    desc = ""
    paras = [p.strip() for p in re.split(r"\n\s*\n", readme) if p.strip() and not p.strip().startswith("#")]
    if paras:
        desc = paras[0][:400]
    return {
        "title": title,
        "description": desc,
        "languages": langs,
        "frameworks": frameworks,
        "readme": readme[:2500],
        "api_routes": routes,
        "plugin_like_folders": folders,
        "domain_keywords": keywords,
        "proposed_abilities": abilities,
    }
