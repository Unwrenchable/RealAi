"""Walk a source tree and emit file fingerprints (skip rules applied)."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Iterator

from realai.learn.skip import MAX_FILE_BYTES, should_skip_dir, should_skip_file, should_skip_rel

FINGERPRINT_CAP = 800


def iter_source_files(root: Path, *, max_bytes: int = MAX_FILE_BYTES) -> Iterator[Path]:
    root = root.resolve()
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames if not should_skip_dir(d))
        rel_dir = Path(dirpath).resolve().relative_to(root)
        rel_dir_s = rel_dir.as_posix()
        if rel_dir_s not in {".", ""} and should_skip_rel(rel_dir_s + "/x"):
            dirnames[:] = []
            continue
        for name in sorted(filenames):
            path = Path(dirpath) / name
            rel = path.resolve().relative_to(root).as_posix()
            if should_skip_rel(rel):
                continue
            if should_skip_file(path, max_bytes=max_bytes):
                continue
            yield path


def _sha1_file(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def fingerprint_file(path: Path, root: Path) -> dict[str, Any]:
    rel = path.resolve().relative_to(root.resolve()).as_posix()
    try:
        size = path.stat().st_size
        digest = _sha1_file(path)
    except OSError as e:
        return {"path": rel, "sha1": "", "bytes": 0, "ext": path.suffix.lower(), "error": str(e)}
    return {
        "path": rel,
        "sha1": digest,
        "bytes": size,
        "ext": path.suffix.lower(),
    }


def scan_tree(
    root: Path,
    *,
    max_files: int = FINGERPRINT_CAP,
    max_bytes: int = MAX_FILE_BYTES,
) -> dict[str, Any]:
    root = root.resolve()
    fps: list[dict[str, Any]] = []
    truncated = False
    for path in iter_source_files(root, max_bytes=max_bytes):
        if len(fps) >= max_files:
            truncated = True
            break
        fps.append(fingerprint_file(path, root))
    return {
        "root": str(root),
        "file_count": len(fps),
        "truncated": truncated,
        "fingerprints": fps,
    }
