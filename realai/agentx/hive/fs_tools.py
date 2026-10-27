"""Read-only filesystem tools for hive agents (safe profile): list_dir, read_file, search.

Every path is resolved inside a per-team workspace root. Denied: anything outside the root
(including symlinks / junctions that resolve outside it), and secret-looking files.
There are no write operations in this module.
"""
from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Any

MAX_READ_BYTES = int(os.environ.get("REALAI_FS_MAX_READ", str(64 * 1024)))
MAX_LIST = 300
MAX_HITS = 60
MAX_SCAN_FILES = 6000
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".next", "dist", "build", "target", ".venv", "venv",
             ".pytest_cache", "coverage", ".vercel", ".anchor"}
SECRET_DIRS = {"keys", "_git_rescue", ".ssh", "secrets", ".secrets"}
SECRET_GLOBS = (".env", ".env.*", "*.env", "id_*", "*.pem", "*.key", "*.p12", "*.pfx", "*keypair*.json",
                "*-keypair.json", "*wallet*.json", "id.json", ".npmrc", ".netrc", "credentials*", "*.keystore")
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".mp3", ".wav", ".ogg", ".mp4", ".webm", ".zip",
              ".gz", ".woff", ".woff2", ".ttf", ".pdf", ".so", ".dll", ".exe", ".bin", ".gguf", ".glb", ".lock"}

TOOL_NAMES = ("list_dir", "read_file", "search")
# Map to the profile tool names in access_profiles.json (safe grants all three).
PROFILE_TOOL = {"list_dir": "list_dir", "read_file": "read_file", "search": "grep_search"}


class FSDenied(Exception):
    pass


def is_secret(rel_parts: tuple[str, ...]) -> bool:
    low = [p.lower() for p in rel_parts]
    if any(p in SECRET_DIRS for p in low[:-1]) or (low and low[-1] in SECRET_DIRS):
        return True
    name = low[-1] if low else ""
    if any(fnmatch.fnmatch(name, g) for g in SECRET_GLOBS):
        return True
    # Solana keypairs: a JSON array of 64 ints, regardless of name.
    return False


def _looks_like_keypair(p: Path) -> bool:
    if p.suffix.lower() != ".json" or p.stat().st_size > 1024:
        return False
    try:
        t = p.read_text(encoding="utf-8", errors="ignore").strip()
    except OSError:
        return False
    return bool(re.fullmatch(r"\[\s*(\d{1,3}\s*,\s*){63}\d{1,3}\s*\]", t))


class SafeFS:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise FSDenied(f"workspace root missing: {root}")
        self.read_log: list[str] = []

    # ---- path safety -------------------------------------------------------
    def resolve(self, rel: str | None) -> Path:
        raw = str(rel or ".").strip().strip("`'\"") or "."
        p = Path(raw)
        cand = p if p.is_absolute() else self.root / p
        real = cand.resolve()  # follows symlinks/junctions
        try:
            parts = real.relative_to(self.root).parts
        except ValueError:
            raise FSDenied("outside workspace root") from None
        if is_secret(parts):
            raise FSDenied("secret path denied")
        if real.is_file() and _looks_like_keypair(real):
            raise FSDenied("secret path denied (keypair)")
        return real

    def rel(self, p: Path) -> str:
        return p.relative_to(self.root).as_posix() or "."

    def exists(self, rel: str) -> bool:
        try:
            return self.resolve(rel).exists()
        except FSDenied:
            return False

    # ---- tools -------------------------------------------------------------
    def list_dir(self, path: str = ".") -> dict[str, Any]:
        d = self.resolve(path)
        if not d.is_dir():
            return {"error": "not a directory", "path": path}
        out = []
        for c in sorted(d.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if c.name in SKIP_DIRS:
                continue
            try:
                self.resolve(str(c))
            except FSDenied:
                continue
            out.append(c.name + ("/" if c.is_dir() else ""))
            if len(out) >= MAX_LIST:
                break
        return {"path": self.rel(d), "entries": out}

    def read_file(self, path: str, offset: int = 0, max_bytes: int | None = None) -> dict[str, Any]:
        f = self.resolve(path)
        if not f.is_file():
            return {"error": "not a file", "path": path}
        if f.suffix.lower() in BINARY_EXT:
            return {"error": "binary file", "path": self.rel(f)}
        cap = min(int(max_bytes or MAX_READ_BYTES), MAX_READ_BYTES)
        with f.open("rb") as fh:
            fh.seek(max(0, int(offset or 0)))
            data = fh.read(cap + 1)
        self.read_log.append(self.rel(f))
        return {"path": self.rel(f), "size": f.stat().st_size, "truncated": len(data) > cap,
                "content": data[:cap].decode("utf-8", errors="replace")}

    def _walk(self, base: Path):
        n = 0
        for dirpath, dirnames, filenames in os.walk(base, followlinks=False):
            dirnames[:] = [x for x in dirnames if x not in SKIP_DIRS and x.lower() not in SECRET_DIRS]
            for fn in filenames:
                p = Path(dirpath) / fn
                n += 1
                if n > MAX_SCAN_FILES:
                    return
                yield p

    def search(self, pattern: str, path: str = ".", glob: str | None = None, max_hits: int = MAX_HITS) -> dict[str, Any]:
        base = self.resolve(path)
        try:
            rx = re.compile(pattern, re.I)
        except re.error:
            rx = re.compile(re.escape(pattern), re.I)
        hits, files = [], []
        for p in self._walk(base):
            if p.suffix.lower() in BINARY_EXT or (glob and not fnmatch.fnmatch(p.name, glob)):
                continue
            try:
                self.resolve(str(p))
                if p.stat().st_size > 2_000_000:
                    continue
                text = p.read_text(encoding="utf-8", errors="ignore")
            except (FSDenied, OSError):
                continue
            rel = self.rel(p.resolve())
            if rx.search(p.name):
                files.append(rel)
            for i, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    hits.append({"path": rel, "line": i, "text": line.strip()[:200]})
                    if len(hits) >= max_hits:
                        return {"pattern": pattern, "hits": hits, "files": files[:50], "truncated": True}
        return {"pattern": pattern, "hits": hits, "files": files[:50], "truncated": False}

    def call(self, name: str, args: dict[str, Any] | None) -> dict[str, Any]:
        args = dict(args or {})
        try:
            if name == "list_dir":
                return self.list_dir(str(args.get("path") or "."))
            if name == "read_file":
                return self.read_file(str(args.get("path") or ""), int(args.get("offset") or 0), args.get("max_bytes"))
            if name == "search":
                return self.search(str(args.get("pattern") or args.get("query") or ""), str(args.get("path") or "."),
                                   args.get("glob"))
        except FSDenied as e:
            return {"error": f"denied: {e}"}
        except (OSError, ValueError, TypeError) as e:
            return {"error": f"{type(e).__name__}"}
        return {"error": f"unknown tool {name!r}; use one of {list(TOOL_NAMES)}"}
