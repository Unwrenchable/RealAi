"""Architect mode: produce a structured architecture report from a compact repo view."""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

from realai.providers import provider_registry

HOME = Path(r"C:\RealAI-clean")
PROMPT_PATH = HOME / "prompts" / "architect_mode.txt"
SNAPSHOT_PATH = HOME / "results" / "repo_snapshot.json"
OUTPUT_PATH = HOME / "results" / "architect_output.txt"

_SKIP_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "recovered",
    "realai_og_mess",
    ".next",
    "dist",
    "build",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    "temp_repos",
    "RealAI_Recovery_SAFE",
    ".agentx",
    ".continue",
    ".kilo",
    "realai.egg-info",
}

_SKIP_PREFIXES = (
    "from-",
    "local-",
    "desktop-",
    "unique-",
    "users-",
    "primary-",
    "plugin-",
    "modules-",
    "recycle-",
    "recovery-",
    "clean_backup",
    "agents-skills-",
    "atomicfizz",
)

_KEY_FILES = (
    "realai.toml",
    "package.json",
    "requirements.txt",
    "realai/cli/craft.py",
    "realai/abilities/architect_mode.py",
    "realai/providers/provider_registry.py",
    "realai/providers/local_llama.py",
    "realai/server/providers.py",
    "realai/v3_orchestrator.py",
    "prompts/architect_mode.txt",
)

_MAX_TREE_LINES = 400
_MAX_PROMPT_CHARS = 10000
_HEAD_CHARS = 400


def _skip_dir(name: str) -> bool:
    low = name.lower()
    if name in _SKIP_DIRS or low in _SKIP_DIRS:
        return True
    if "copy" in low or "recovery" in low or "backup" in low:
        return True
    return any(low.startswith(p) for p in _SKIP_PREFIXES)


def _compact_repo_view(root: Path) -> str:
    ext_counts: Counter[str] = Counter()
    files: list[str] = []
    top = sorted(p.name + ("/" if p.is_dir() else "") for p in root.iterdir())
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if not _skip_dir(d))
        rel_dir = Path(dirpath).relative_to(root)
        if any(_skip_dir(part) for part in rel_dir.parts):
            dirnames[:] = []
            continue
        depth = len(rel_dir.parts) if rel_dir.parts != (".",) else 0
        if depth > 5:
            dirnames[:] = []
            continue
        for name in sorted(filenames):
            if name.endswith((".pyc", ".pyo", ".map")):
                continue
            rel = str((rel_dir / name).as_posix()) if rel_dir.parts else name
            ext = Path(name).suffix.lower() or "(none)"
            ext_counts[ext] += 1
            if len(files) < _MAX_TREE_LINES:
                files.append(rel)

    heads: list[str] = []
    for rel in _KEY_FILES:
        fp = root / rel
        if not fp.is_file():
            continue
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")[:_HEAD_CHARS]
        except OSError:
            continue
        heads.append(f"### {rel}\n{text}\n")

    snap_size = SNAPSHOT_PATH.stat().st_size if SNAPSHOT_PATH.is_file() else 0
    lines = [
        f"ROOT: {root}",
        f"FULL_SNAPSHOT: {SNAPSHOT_PATH} ({snap_size} bytes) — too large for model context; using compact live view.",
        "",
        "TOP-LEVEL:",
        *[f"  {name}" for name in top[:80]],
        "",
        "EXTENSION COUNTS (live, skipped dumps):",
        *[f"  {ext}: {n}" for ext, n in ext_counts.most_common(20)],
        "",
        f"FILE TREE ({len(files)} listed, depth<=5):",
        *files,
        "",
        "KEY FILE HEADS:",
        *heads,
    ]
    return "\n".join(lines)


def run_architect_mode() -> dict:
    if not PROMPT_PATH.is_file():
        return {"ok": False, "summary": "Prompt file does not exist."}
    if not SNAPSHOT_PATH.is_file():
        return {"ok": False, "summary": "Repo snapshot file does not exist."}

    prompt = PROMPT_PATH.read_text(encoding="utf-8", errors="replace")
    snapshot_view = _compact_repo_view(HOME)
    full_prompt = prompt + "\n\n---\n\nRepo Snapshot (compact live view):\n" + snapshot_view
    if len(full_prompt) > _MAX_PROMPT_CHARS:
        full_prompt = full_prompt[:_MAX_PROMPT_CHARS] + "\n\n[truncated for local context window]\n"

    model = provider_registry.load_default_model()
    if not model:
        return {"ok": False, "summary": "Failed to load default model (local llama server not reachable)."}

    try:
        output = model.create_completion(
            prompt=full_prompt,
            max_tokens=2048,
            temperature=0.2,
            n=1,
            stop=None,
        )
    except Exception as e:
        return {"ok": False, "summary": f"Model call failed: {e}"}

    if isinstance(output, dict):
        choices = output.get("choices") or []
        if choices:
            output = choices[0].get("text") or (choices[0].get("message") or {}).get("content") or ""
        else:
            output = output.get("content") or output.get("text") or ""
    output = str(output or "").strip()
    if not output:
        return {"ok": False, "summary": "Model output is empty."}
    letters = [ch for ch in output if not ch.isspace()]
    if letters:
        top = max(letters, key=letters.count)
        if letters.count(top) / len(letters) > 0.4:
            return {
                "ok": False,
                "summary": f"Model output was degenerate (repeated {top!r}). Retry /architect_mode.",
            }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(output, encoding="utf-8")
    return {"ok": True, "summary": "Architect analysis written.", "path": str(OUTPUT_PATH)}
