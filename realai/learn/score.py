"""Score learned tree paths for adapt-as-hive wiring (never copy foreign code)."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_SKIP_PARTS = {
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "vendor",
    "dist",
    "build",
    ".next",
    "coverage",
    ".before",
    "_quarantine",
    "recovery",
    "hf_cache",
    ".cache",
    "test",
    "tests",
    "__tests__",
    "fixtures",
}

_SKIP_SUFFIX = {".min.js", ".map", ".lock", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".woff", ".woff2"}

_ABILITY_HINT = re.compile(
    r"(?i)(ability|abilities|skill|coach|handler|service|controller|route|api|endpoint)"
)
_PLUGIN_HINT = re.compile(r"(?i)(plugin|plugins|\.github/agents|extension|addon)")
_AGENT_HINT = re.compile(r"(?i)(agent|agents|overseer|planner|worker|critic)")
_ORGAN_HINT = re.compile(r"(?i)(organ|organs|module|modules/)")
_TOOL_HINT = re.compile(r"(?i)(tool|tools|cli|script|bin/)")


def _should_skip(rel: str) -> bool:
    parts = {p.lower() for p in rel.replace("\\", "/").split("/") if p}
    if parts & _SKIP_PARTS:
        return True
    low = rel.lower()
    if any(low.endswith(s) for s in _SKIP_SUFFIX):
        return True
    if "config.json" in low and ("hf" in low or "transformers" in low):
        return True
    if ".before" in low or low.endswith(".park"):
        return True
    return False


def _kind_for(rel: str, signals: dict[str, Any]) -> str:
    low = rel.replace("\\", "/").lower()
    folders = [str(x).lower() for x in (signals.get("plugin_like_folders") or [])]
    if any(low.startswith(f.rstrip("/") + "/") or low == f.rstrip("/") for f in folders):
        return "plugin"
    if _AGENT_HINT.search(low):
        return "agent"
    if _PLUGIN_HINT.search(low):
        return "plugin"
    if _ORGAN_HINT.search(low) and ("realai" in low or "module" in low):
        return "organ"
    if _TOOL_HINT.search(low):
        return "tool"
    if _ABILITY_HINT.search(low):
        return "ability"
    # framework routes
    routes = [str(r).lower() for r in (signals.get("api_routes") or [])]
    if any(r in low for r in routes if len(r) > 3):
        return "ability"
    if low.endswith((".py", ".ts", ".js", ".mjs")):
        return "tool"
    return "skip"


def _score_row(rel: str, kind: str, signals: dict[str, Any]) -> tuple[int, str, str]:
    """Return score, why, adapt."""
    if kind == "skip":
        return 0, "noise or vendor path", "skip — do not copy"
    score = 20
    why_bits: list[str] = []
    fws = [str(x).lower() for x in (signals.get("frameworks") or [])]
    kws = [str(x).lower() for x in (signals.get("domain_keywords") or [])]
    low = rel.lower()

    if kind == "plugin":
        score += 35
        why_bits.append("plugin-like surface")
    elif kind == "ability":
        score += 30
        why_bits.append("ability/route surface")
    elif kind == "agent":
        score += 28
        why_bits.append("agent-shaped path")
    elif kind == "organ":
        score += 15
        why_bits.append("organ/module-shaped")
    elif kind == "tool":
        score += 18
        why_bits.append("tool/script surface")

    for fw in fws:
        if fw and fw in low:
            score += 8
            why_bits.append(f"framework:{fw}")
            break
    hit_kw = [k for k in kws[:12] if k and k in low.replace("/", "_").replace("-", "_")]
    if hit_kw:
        score += min(15, 5 * len(hit_kw[:3]))
        why_bits.append("keywords:" + ",".join(hit_kw[:3]))

    if low.endswith("readme.md") or low.endswith("package.json"):
        score += 5
        why_bits.append("entrypoint metadata")

    score = max(0, min(100, score))
    adapt_map = {
        "ability": "wrap as hive ability (invoke learned module — never copy file)",
        "plugin": "wrap as hive learned plugin package — never copy file",
        "agent": "wrap as hive agent task bridge — never copy file",
        "organ": "skip organ promote — document only",
        "tool": "wrap as hive tool adapter — never copy file",
    }
    why = "; ".join(why_bits) if why_bits else f"{kind} candidate"
    return score, why, adapt_map.get(kind, "skip — do not copy")


def score_source(
    root: Path,
    fingerprints: list[dict[str, Any]] | None,
    signals: dict[str, Any] | None,
    *,
    cap: int = 40,
) -> list[dict[str, Any]]:
    """Rank top dirs + notable files. Cap rows. Never suggests copying foreign code."""
    root = Path(root)
    signals = signals or {}
    fps = list(fingerprints or [])
    candidates: list[str] = []

    # Top-level dirs
    try:
        for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
            if child.is_dir() and child.name.lower() not in _SKIP_PARTS and not child.name.startswith("."):
                candidates.append(child.name.replace("\\", "/"))
    except OSError:
        pass

    # Plugin-like folders from signals
    for folder in signals.get("plugin_like_folders") or []:
        candidates.append(str(folder).replace("\\", "/"))

    # Fingerprint paths
    for fp in fps:
        if not isinstance(fp, dict):
            continue
        rel = str(fp.get("path") or fp.get("rel") or "").replace("\\", "/")
        if rel:
            candidates.append(rel)

    # Notable filenames under shallow roots
    for name in ("package.json", "README.md", "pyproject.toml", "server.js", "index.js", "app.py", "main.py"):
        if (root / name).is_file():
            candidates.append(name)

    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for rel in candidates:
        rel = rel.strip().lstrip("./")
        if not rel or rel.lower() in seen:
            continue
        seen.add(rel.lower())
        if _should_skip(rel):
            kind = "skip"
        else:
            kind = _kind_for(rel, signals)
        score, why, adapt = _score_row(rel, kind, signals)
        if kind == "skip" and score == 0:
            # keep a few skip examples only if explicitly vendor-ish and under cap later
            continue
        rows.append(
            {
                "path": rel,
                "kind": kind,
                "score": score,
                "why": why,
                "adapt": adapt,
            }
        )

    rows.sort(key=lambda r: (-int(r["score"]), r["path"]))
    # Ensure some skip samples if we filtered all — optional, prefer high scores
    return rows[: max(1, int(cap))]
