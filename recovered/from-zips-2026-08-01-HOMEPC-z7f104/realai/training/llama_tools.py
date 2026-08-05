"""Discover vendored or system llama.cpp binaries for export/inference."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_root() -> Path:
    return _REPO_ROOT


def _candidates(names: List[str], extra_dirs: Optional[List[Path]] = None) -> List[Path]:
    paths: List[Path] = []
    for name in names:
        found = shutil.which(name)
        if found:
            paths.append(Path(found))
    dirs = list(extra_dirs or [])
    dirs.extend(
        [
            _REPO_ROOT / "vendor" / "llama.cpp" / "b4400",
            _REPO_ROOT / "vendor" / "llama.cpp" / "b9663" / "llama-b9663",
        ]
    )
    env_root = os.environ.get("REALAI_LLAMA_CPP_ROOT", "").strip()
    if env_root:
        dirs.append(Path(env_root).expanduser())
        dirs.append(Path(env_root).expanduser() / "build" / "bin")
        dirs.append(Path(env_root).expanduser() / "build" / "bin" / "Release")
    for directory in dirs:
        if not directory.is_dir():
            continue
        for name in names:
            for variant in (name, f"{name}.exe"):
                candidate = directory / variant
                if candidate.is_file():
                    paths.append(candidate)
    return paths


def find_llama_quantize() -> Optional[Path]:
    for path in _candidates(["llama-quantize", "quantize"]):
        if path.is_file():
            return path
    return None


def find_llama_cli() -> Optional[Path]:
    for path in _candidates(["llama-cli", "llama"]):
        if path.is_file():
            return path
    return None


def find_convert_hf_script() -> Optional[Path]:
    """Locate convert_hf_to_gguf.py from a llama.cpp checkout."""
    env = os.environ.get("REALAI_LLAMA_CPP_ROOT", "").strip()
    search_roots: List[Path] = []
    if env:
        search_roots.append(Path(env).expanduser())
    search_roots.extend(
        [
            _REPO_ROOT / "vendor" / "llama.cpp",
            Path.home() / "llama.cpp",
            Path("C:/llama.cpp"),
        ]
    )
    rel_paths = [
        Path("convert_hf_to_gguf.py"),
        Path("tools") / "convert_hf_to_gguf.py",
        Path("gguf-py") / "gguf" / "scripts" / "convert_hf_to_gguf.py",
    ]
    for root in search_roots:
        if not root.is_dir():
            continue
        for rel in rel_paths:
            candidate = (root / rel).resolve()
            if candidate.is_file():
                return candidate
    return None


def python_for_llama_convert() -> str:
    return os.environ.get("REALAI_PYTHON", sys.executable)