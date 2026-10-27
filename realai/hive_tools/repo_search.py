"""repo_search: read-only list / grep / read over a LOCAL mirror of Travis's own repos (tool 32).

The mirror is built separately by ``tools/repo_mirror.py`` (shallow clones under D:\\ARCHIVE, secret-bearing
files never checked out, SHA256 manifest, types-only secrets report). This tool only reads it:

  * root      REALAI_REPO_MIRROR, else D:\\ARCHIVE\\repo-mirror (Windows) - never anything outside it
  * allowlist REPOS below (searchable ones) AND present in the mirror; LustLink and the skipped repos are not here
  * blocked   .git, vendor/build dirs, .env*/.npmrc/key/credential/wallet files, files the mirror's secret scan
              flagged (manifest ``blocked``), binaries, files > 512 KB, paths that escape the repo (.., absolute,
              drive letters, symlinks out)
  * output    capped at ~4 KB (tool_json limit), every line passed through secret redaction (``<redacted:type>``)
  * no network, no writes, deterministic for the same mirror (sorted walk) so the verifier can recompute.

Opt-out: REALAI_REPO_SEARCH=0 removes it from the live catalog (default on).
"""
from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Tuple

from realai.hive_tools.extended import _fn

# name -> tier, money flag, searchable, holdout (eval-only rows), canonical source. Approved plan 2026-10-19.
# Not listed (never mirrored/searched): LustLink (excluded), reverse-phone-search, Productivitybot, Domain-bot,
# atomicfizzcaps + ATOMIC-...-GPS (duplicates of the canonical -main), empty/tiny/vendored repos, forks' upstreams.
REPOS: Dict[str, Dict[str, Any]] = {
    "RealAi": {"tier": "core"},
    "ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS-main": {"tier": "core", "money": True, "alias": "atomic-fizz"},
    "Rack_em_up": {"tier": "core", "alias": "rackup"},
    "overseer-bot-ai": {"tier": "core"},
    "overseer-bot-ui": {"tier": "core"},
    "agent-tools": {"tier": "core"},
    "FizzSwap": {"tier": "restricted", "money": True},
    "cookbook": {"tier": "restricted", "money": True},
    "Token-scalper": {"tier": "refusal_only", "money": True, "searchable": False},
    "9dttt": {"tier": "useful"},
    "Cue-guard": {"tier": "useful", "money": True},
    "effective-engine": {"tier": "useful"},
    "supreme-goggles": {"tier": "useful"},
    "EditPro": {"tier": "useful"},
    "crispy-octo-guacamole": {"tier": "useful", "holdout": True},
    "BlueScreenHelp": {"tier": "useful", "holdout": True},
    "speedRouter": {"tier": "useful"},
    "improved-enigma": {"tier": "useful"},
    "Side-Pocket": {"tier": "useful"},
    "fluffy-memory": {"tier": "useful"},
}
EXCLUDED_REPOS = ("LustLink", "reverse-phone-search", "Productivitybot", "Domain-bot")
OWNER = "Unwrenchable"

BLOCKED_DIRS = {".git", "node_modules", "vendor", "dist", "build", ".next", "out", "coverage", "__pycache__", ".venv",
                "venv", "env", ".cache", ".turbo", "target", "bower_components", ".idea", ".vscode"}
_BLOCKED_NAME = re.compile(
    r"(?i)^(\.env(\..*)?|\.npmrc|\.pypirc|\.netrc|\.git-credentials|id_(rsa|dsa|ecdsa|ed25519)(\.pub)?|.*\.(pem|key|p12|pfx|"
    r"keystore|jks|kdbx)|.*credential.*|.*secret.*\.(json|ya?ml|txt|env)|.*(wallet|keypair|mnemonic|seed[-_]?phrase).*\.(json|txt))$")
_ALLOWED_DOTENV = re.compile(r"(?i)^\.env\.(example|sample|template)$")
BINARY_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".bmp", ".svgz", ".mp3", ".mp4", ".wav", ".ogg", ".webm", ".mov",
              ".zip", ".gz", ".tgz", ".7z", ".rar", ".pdf", ".woff", ".woff2", ".ttf", ".otf", ".eot", ".exe", ".dll", ".so",
              ".dylib", ".bin", ".gguf", ".safetensors", ".pt", ".onnx", ".pyc", ".class", ".jar", ".wasm", ".psd", ".sqlite",
              ".sqlite3", ".db", ".lock"}
MAX_FILE_BYTES = 512 * 1024
OUT_LIMIT = 4000
GREP_HITS = 12
GREP_FILES = 4000
READ_LINES = 60
LIST_ITEMS = 60
LINE_CHARS = 200

_EXTRA_SECRETS: List[Tuple[str, re.Pattern]] = [
    ("assigned_secret", re.compile(r"(?i)((?:api[_-]?key|secret|token|passw(?:or)?d|private[_-]?key|mnemonic|seed[_-]?phrase|"
                                   r"client[_-]?secret|auth)[\w-]*[\"']?\s*[:=]\s*[\"']?)([^\s\"',;]{8,})")),
    ("hex_key", re.compile(r"\b0x[0-9a-fA-F]{64}\b")),
    ("base58_key", re.compile(r"\b[1-9A-HJ-NP-Za-km-z]{80,90}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("url_credentials", re.compile(r"(?i)\b[a-z][a-z0-9+.-]*://[^\s:/@]+:[^\s@/]{3,}@")),
]

_S = {"type": "string"}
SPECS: Dict[str, Dict[str, Any]] = {
    "repo_search": _fn(
        "repo_search",
        "Read-only search of the local mirror of Travis's own repos (RackUp, Atomic Fizz, Overseer, agent-tools, RealAi...): "
        "list (repos, or a folder), grep (literal text), read (file lines). Cite repo:path:line. Never edits; secret files blocked.",
        {"action": {"type": "string", "enum": ["list", "grep", "read"]}, "repo": _S, "path": _S, "query": _S,
         "start_line": {"type": "integer"}, "end_line": {"type": "integer"}},
        ["action"]),
}


def enabled() -> bool:
    return os.environ.get("REALAI_REPO_SEARCH", "1").strip().lower() not in ("0", "false", "no", "off")


def mirror_root(ctx: Optional[Dict[str, Any]] = None) -> Optional[Path]:
    v = (ctx or {}).get("repo_mirror") or os.environ.get("REALAI_REPO_MIRROR")
    if v:
        return Path(v)
    if os.name == "nt":
        return Path(r"D:\ARCHIVE\repo-mirror")
    return None


@lru_cache(maxsize=8)
def _manifest(root: str, mtime: float) -> Dict[str, Any]:
    p = Path(root) / "repo_mirror_manifest.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def manifest(root: Path) -> Dict[str, Any]:
    p = root / "repo_mirror_manifest.json"
    return _manifest(str(root), p.stat().st_mtime if p.is_file() else 0.0)


def searchable(name: str) -> bool:
    meta = REPOS.get(name)
    return bool(meta) and meta.get("searchable", True) and name not in EXCLUDED_REPOS


def available(root: Optional[Path]) -> List[str]:
    if root is None or not root.is_dir():
        return []
    return [n for n in sorted(REPOS) if searchable(n) and (root / n).is_dir()]


def resolve_repo(name: str) -> Optional[str]:
    n = str(name or "").strip().strip("/").split("/")[-1].lower()
    if not n:
        return None
    for k, m in REPOS.items():
        if n in (k.lower(), str(m.get("alias", "")).lower()):
            return k
    return None


def find_secret_types(text: str) -> List[str]:
    from realai.training.dataset_builder.scrub import find_secrets

    return sorted(set(find_secrets(text)) | {n for n, p in _EXTRA_SECRETS if p.search(text or "")})


def redact(text: str) -> Tuple[str, int]:
    from realai.training.dataset_builder.scrub import SECRET_PATTERNS

    n = 0
    out = text
    for name, pat in SECRET_PATTERNS:
        out, k = pat.subn(f"<redacted:{name}>", out)
        n += k
    for name, pat in _EXTRA_SECRETS:
        if name == "assigned_secret":
            out, k = pat.subn(lambda m: m.group(1) + "<redacted:secret>", out)
        else:
            out, k = pat.subn(f"<redacted:{name}>", out)
        n += k
    return out, n


def blocked_name(part: str) -> bool:
    if _ALLOWED_DOTENV.match(part):
        return False
    return part in BLOCKED_DIRS or bool(_BLOCKED_NAME.match(part))


def _clean_rel(path: str) -> Optional[str]:
    """'' for the repo root; None if the path is absolute, has a drive/UNC prefix or climbs out with '..'."""
    s = str(path or "").replace("\\", "/").strip()
    if s in ("", ".", "/"):
        return ""
    if s.startswith("/") or s.startswith("~") or re.match(r"^[A-Za-z]:", s) or s.startswith("//"):
        return None
    parts = [p for p in PurePosixPath(s).parts if p not in ("", ".")]
    if any(p == ".." for p in parts):
        return None
    return "/".join(parts)


def _inside(p: Path, base: Path) -> bool:
    try:
        p.resolve().relative_to(base.resolve())
        return True
    except (ValueError, OSError):
        return False


def _is_blocked(rel: str, repo: str, man: Dict[str, Any]) -> Optional[str]:
    parts = rel.split("/") if rel else []
    for part in parts:
        if blocked_name(part):
            return "blocked path (secret-bearing, vendored or VCS file)"
    blocked = set(((man.get("repos") or {}).get(repo) or {}).get("blocked") or [])
    if rel in blocked:
        return "blocked by the mirror's secret scan"
    if parts and Path(parts[-1]).suffix.lower() in BINARY_EXT:
        return "binary or lock file"
    return None


def _text(p: Path) -> Optional[str]:
    try:
        if p.stat().st_size > MAX_FILE_BYTES:
            return None
        raw = p.read_bytes()
    except OSError:
        return None
    if b"\0" in raw[:4096]:
        return None
    return raw.decode("utf-8", errors="replace")


def _walk(base: Path, repo: str, man: Dict[str, Any]):
    """Sorted, deterministic walk of allowed text files: yields (rel, path)."""
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if not blocked_name(d) and not os.path.islink(os.path.join(dirpath, d)))
        for fn in sorted(filenames):
            p = Path(dirpath) / fn
            rel = p.relative_to(base).as_posix()
            if p.is_symlink() or _is_blocked(rel, repo, man):
                continue
            yield rel, p


def _line(s: str) -> Tuple[str, int]:
    s = s.rstrip("\r\n")
    s = s if len(s) <= LINE_CHARS else s[: LINE_CHARS - 1] + "…"
    return redact(s)


def _fit(out: Dict[str, Any], key: str) -> Dict[str, Any]:
    """Drop trailing items of out[key] until the compact JSON fits OUT_LIMIT."""
    items = out.get(key) or []
    while items and len(json.dumps(out, ensure_ascii=False, separators=(",", ":"))) > OUT_LIMIT:
        items.pop()
        out["truncated"] = True
    return out


def repo_search(args: Dict[str, Any], ctx: Dict[str, Any]) -> Dict[str, Any]:
    action = str(args.get("action") or "").strip().lower() or ("grep" if args.get("query") else "list")
    root = mirror_root(ctx)
    if root is None or not root.is_dir():
        return {"ok": False, "error": "repo mirror not available (run tools/repo_mirror.py; set REALAI_REPO_MIRROR)"}
    man = manifest(root)
    have = available(root)
    raw_repo = str(args.get("repo") or "").strip()
    repo = resolve_repo(raw_repo) if raw_repo else None
    if raw_repo and (repo is None or not searchable(repo)):
        return {"ok": False, "error": f"repo {raw_repo!r} is not in the searchable allowlist", "repos": have}
    if repo and repo not in have:
        return {"ok": False, "error": f"repo {repo!r} is not mirrored", "repos": have}
    commit = lambda r: ((man.get("repos") or {}).get(r) or {}).get("commit", "")[:12]  # noqa: E731

    if action == "list" and not repo:
        return {"ok": bool(have), "action": "list", "repos": [{"repo": r, "tier": REPOS[r]["tier"], "commit": commit(r)} for r in have],
                **({} if have else {"error": "mirror is empty"}), "note": "read-only mirror"}
    rel = _clean_rel(str(args.get("path") or ""))
    if rel is None:
        return {"ok": False, "error": "path must be relative to the repo (no absolute paths or '..')"}
    if action in ("list", "read") and not repo:
        return {"ok": False, "error": "need repo", "repos": have}

    if action == "grep":
        q = str(args.get("query") or "").strip()
        if len(q) < 2:
            return {"ok": False, "error": "need query (literal text, 2+ chars)"}
        ql = q.lower()
        hits: List[Dict[str, Any]] = []
        nred, scanned = 0, 0
        for r in ([repo] if repo else have):
            base = root / r
            sub = base / rel if rel else base
            if rel and (_is_blocked(rel, r, man) or not _inside(sub, base)):
                return {"ok": False, "error": "blocked path"}
            if not sub.exists():
                continue
            files = [(rel, sub)] if sub.is_file() else ((f"{rel}/{x}" if rel else x, p) for x, p in _walk(sub, r, man))
            for frel, p in files:
                scanned += 1
                if scanned > GREP_FILES or len(hits) >= GREP_HITS:
                    break
                t = _text(p)
                if t is None or ql not in t.lower():
                    continue
                for i, ln in enumerate(t.splitlines(), 1):
                    if ql in ln.lower():
                        s, k = _line(ln.strip())
                        nred += k
                        hits.append({"repo": r, "path": frel, "line": i, "text": s})
                        if len(hits) >= GREP_HITS:
                            break
        if not hits:
            return {"ok": False, "action": "grep", "query": q, "repo": repo, "error": "no matches", "files_scanned": min(scanned, GREP_FILES)}
        out = {"ok": True, "action": "grep", "query": q, "repo": repo, "hits": hits,
               "truncated": len(hits) >= GREP_HITS or scanned > GREP_FILES, "redacted": nred}
        return _fit(out, "hits")

    base = root / repo
    target = base / rel if rel else base
    why = _is_blocked(rel, repo, man) if rel else None
    if why:
        return {"ok": False, "repo": repo, "path": rel, "error": why}
    if not _inside(target, base):
        return {"ok": False, "error": "path escapes the repo"}
    if not target.exists():
        return {"ok": False, "repo": repo, "path": rel, "error": "not found"}

    if action == "list":
        if not target.is_dir():
            return {"ok": False, "repo": repo, "path": rel, "error": "not a directory (use read)"}
        entries = []
        for p in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if p.is_symlink() or blocked_name(p.name) or (p.is_file() and _is_blocked(f"{rel}/{p.name}" if rel else p.name, repo, man)):
                continue
            entries.append(p.name + ("/" if p.is_dir() else ""))
        total = len(entries)
        out = {"ok": True, "action": "list", "repo": repo, "path": rel or ".", "commit": commit(repo), "entries": entries[:LIST_ITEMS],
               "count": total, "truncated": total > LIST_ITEMS}
        return _fit(out, "entries")

    if action == "read":
        if not target.is_file():
            return {"ok": False, "repo": repo, "path": rel, "error": "not a file (use list)"}
        t = _text(target)
        if t is None:
            return {"ok": False, "repo": repo, "path": rel, "error": "binary or larger than 512 KB"}
        lines = t.splitlines()
        a = max(1, int(args.get("start_line") or 1))
        b = int(args.get("end_line") or (a + READ_LINES - 1))
        b = min(len(lines), max(a, min(b, a + READ_LINES - 1)))
        nred = 0
        body = []
        for i in range(a, b + 1):
            s, k = _line(lines[i - 1])
            nred += k
            body.append(f"{i}: {s}")
        out = {"ok": True, "action": "read", "repo": repo, "path": rel, "commit": commit(repo), "start_line": a, "end_line": b,
               "total_lines": len(lines), "lines": body, "redacted": nred}
        out = _fit(out, "lines")
        if out.get("truncated"):
            out["end_line"] = a + len(out["lines"]) - 1
        return out
    return {"ok": False, "error": f"unknown action {action!r} (list, grep, read)"}


EXECUTORS = {"repo_search": repo_search}

_CITE = re.compile(r"(?<![\w/.-])((?:[\w.-]+/)+[\w.-]+\.\w{1,6}|[\w-]+\.(?:py|ts|tsx|js|jsx|md|json|sol|sql|html|css|yml|yaml|toml|rs|go|sh|ps1|txt))(?::\d+)?")


def key_facts(name: str, r: Dict[str, Any], args: Dict[str, Any]) -> List[List[str]]:
    if not r.get("ok"):
        return []
    if r.get("action") == "grep":
        alts = []
        for h in r.get("hits") or []:
            alts += [h["path"], h["path"].rsplit("/", 1)[-1]]
        return [sorted(set(alts))]
    if r.get("action") == "read":
        return [[r["path"], r["path"].rsplit("/", 1)[-1]]]
    if r.get("action") == "list":
        if r.get("repos") is not None and "entries" not in r:
            return [[x["repo"] for x in r["repos"]]]
        return [[e.rstrip("/") for e in r.get("entries") or []]]
    return []


def cited_paths(answer: str) -> List[str]:
    """File paths an answer cites (``src/app.ts``, ``README.md:12``)."""
    return sorted({m.group(1) for m in _CITE.finditer(answer or "")})


def ungrounded_citations(answer: str, results: List[Dict[str, Any]], question: str = "") -> List[str]:
    """Cited paths that no repo_search result (or the question) mentions: invented file names."""
    blob = json.dumps(results, ensure_ascii=False) + " " + (question or "")
    return [p for p in cited_paths(answer) if p not in blob and p.rsplit("/", 1)[-1] not in blob]
