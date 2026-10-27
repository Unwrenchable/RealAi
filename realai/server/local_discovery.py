"""Local model / llama-cli discovery (ported from RealAi-unified).

Sources: RealAi-unified ``realai_local_server.py`` (_discover_llama_cli,
_discover_model_path) and ``realai/server/config.py``
(_discover_local_model_candidates, _resolve_model_path).

Pure functions, no import-time scanning. Live's Windows-first lookups in
``llama_cli_backend`` / ``realai_local_server`` still run first; these add the
POSIX locations and env overrides. Upstream also rglob'd ``~/Downloads`` and
``/mnt/c/Users``; those were dropped (unbounded scans of user folders).
"""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import List, Optional

MODEL_PATTERNS = ("*.gguf", "*.bin", "*.safetensors", "*.onnx", "*.pt", "*.pth")
_REPO_ROOT = Path(__file__).resolve().parents[2]


def discover_llama_cli() -> Optional[str]:
    for env in ("REALAI_LLAMA_CLI_PATH", "REALAI_LLAMA_CLI"):
        configured = os.getenv(env)
        if configured and Path(configured).exists():
            return str(Path(configured))
    for name in ("llama-cli", "llama-cli.exe", "llama", "llama-simple", "llama-simple.exe"):
        found = shutil.which(name)
        if found:
            return found
    for candidate in (
        Path.home() / ".local" / "bin" / "llama-cli",
        Path.home() / ".local" / "bin" / "llama",
        Path.home() / "bin" / "llama-cli",
        Path.home() / "bin" / "llama",
        Path("/usr/local/bin/llama-cli"),
        Path("/usr/local/bin/llama"),
        Path("/opt/llama.cpp/bin/llama-cli"),
        Path("/opt/llama.cpp/bin/llama"),
    ):
        if candidate.exists():
            return str(candidate)
    return None


def model_search_roots() -> List[Path]:
    roots = [
        Path.home() / ".realai" / "models",
        Path.home() / "models",
        Path("/opt/realai/models"),
        Path("/opt/models"),
        Path("/mnt/d/Models"),
        Path("/usr/share/models"),
        Path("models"),
        _REPO_ROOT / "models",
    ]
    extra = os.getenv("REALAI_MODELS_DIR")
    if extra:
        roots.insert(0, Path(extra))
    return roots


def discover_local_model_candidates(roots: Optional[List[Path]] = None) -> List[Path]:
    seen = set()
    out: List[Path] = []
    for root in roots if roots is not None else model_search_roots():
        if not root.exists():
            continue
        for pattern in MODEL_PATTERNS:
            for cand in sorted(root.rglob(pattern)):
                key = str(cand.resolve())
                if cand.is_file() and key not in seen:
                    seen.add(key)
                    out.append(cand)
    return out


def discover_model_path() -> Optional[str]:
    configured = os.getenv("REALAI_MODEL_PATH")
    if configured and Path(configured).exists():
        return str(Path(configured))
    found = discover_local_model_candidates()
    return str(found[0]) if found else None


def resolve_model_path(raw_path: Optional[str], roots: Optional[List[Path]] = None) -> Optional[str]:
    """Resolve a registry ``path`` to a real file; relative names are searched for."""
    if not raw_path:
        return None
    path = Path(raw_path)
    if path.exists():
        return str(path)
    if path.is_absolute():
        return None
    for cand in discover_local_model_candidates(roots):
        if cand.name.lower() == path.name.lower() or str(cand).endswith(str(path)):
            return str(cand)
    return None
