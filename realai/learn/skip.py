"""Skip rules for git-learn tree walks (.gitignore-ish, no git binary required)."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

# Directory basenames skipped anywhere in the relative path.
SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        ".env",
        "dist",
        "build",
        ".next",
        ".nuxt",
        ".turbo",
        ".tox",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".cache",
        "coverage",
        "htmlcov",
        "vendor",
        "site-packages",
        ".hive",
        ".kilo",
        ".agentx",
        ".grok",
        ".learn_cache",
        "logs",
        "cache",
        "_quarantine",
        "recovered",
        "archive",
        ".idea",
        ".vscode",
        ".eggs",
        "*.egg-info",
        ".tox",
        "out",
    }
)

# Exact filenames skipped (lockfiles + noise).
SKIP_FILE_NAMES = frozenset(
    {
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "bun.lock",
        "bun.lockb",
        "poetry.lock",
        "cargo.lock",
        "composer.lock",
        "gemfile.lock",
        "pipfile.lock",
        "go.sum",
        ".ds_store",
        "thumbs.db",
    }
)

# Suffixes treated as binaries / generated / huge artifacts.
SKIP_SUFFIXES = frozenset(
    {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".ico",
        ".bmp",
        ".svgz",
        ".mp3",
        ".mp4",
        ".mov",
        ".wav",
        ".webm",
        ".ogg",
        ".bin",
        ".exe",
        ".dll",
        ".so",
        ".dylib",
        ".wasm",
        ".gguf",
        ".onnx",
        ".h5",
        ".pt",
        ".pth",
        ".safetensors",
        ".woff",
        ".woff2",
        ".ttf",
        ".otf",
        ".eot",
        ".zip",
        ".gz",
        ".tgz",
        ".bz2",
        ".7z",
        ".rar",
        ".pdf",
        ".wasm",
        ".pyc",
        ".pyo",
        ".class",
        ".o",
        ".a",
        ".lib",
        ".map",
        ".min.js",
        ".min.css",
    }
)

MAX_FILE_BYTES = 1_000_000  # 1 MiB — large files are skipped, not fingerprinted


def _norm_name(name: str) -> str:
    return (name or "").strip().lower()


def should_skip_dir(name: str) -> bool:
    n = _norm_name(name)
    if not n or n in SKIP_DIR_NAMES:
        return True
    if n.endswith(".egg-info"):
        return True
    return False


def should_skip_filename(name: str) -> bool:
    n = _norm_name(name)
    if n in SKIP_FILE_NAMES:
        return True
    if n.endswith(".min.js") or n.endswith(".min.css"):
        return True
    suffix = Path(n).suffix
    if suffix in SKIP_SUFFIXES:
        return True
    # double-suffix minified maps
    if n.endswith(".js.map") or n.endswith(".css.map"):
        return True
    return False


def should_skip_rel(rel: str, *, parts: Iterable[str] | None = None) -> bool:
    """True when a repo-relative path should be skipped (dirs or filename)."""
    raw = (rel or "").replace("\\", "/").strip()
    if not raw:
        return True
    segs = list(parts) if parts is not None else [p for p in raw.split("/") if p and p != "."]
    if not segs:
        return True
    for dir_part in segs[:-1]:
        if should_skip_dir(dir_part):
            return True
    if should_skip_dir(segs[-1]) and len(segs) > 1 and "." not in segs[-1]:
        return True
    return should_skip_filename(segs[-1])


def should_skip_file(path: Path, *, max_bytes: int = MAX_FILE_BYTES) -> bool:
    """Skip by name/suffix, then by size. Missing files are skipped."""
    if should_skip_filename(path.name):
        return True
    try:
        if not path.is_file():
            return True
        if path.stat().st_size > max_bytes:
            return True
    except OSError:
        return True
    return False
