"""Walk a source tree (and every git branch) and emit file fingerprints."""
from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path
from typing import Any, Iterator

from realai.learn.skip import MAX_FILE_BYTES, should_skip_dir, should_skip_file, should_skip_rel
from realai.learn.source import (
    git_bytes,
    git_capture,
    git_env,
    is_git_work_tree,
    ordered_branch_refs,
)

FINGERPRINT_CAP = 5000
DEFAULT_MAX_BRANCHES = 40


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
    branch_label: str = "",
) -> dict[str, Any]:
    root = root.resolve()
    fps: list[dict[str, Any]] = []
    truncated = False
    for path in iter_source_files(root, max_bytes=max_bytes):
        if len(fps) >= max_files:
            truncated = True
            break
        fp = fingerprint_file(path, root)
        if branch_label:
            fp["seen_on_branches"] = [branch_label]
        fps.append(fp)
    seen = [branch_label] if branch_label else []
    counts = {branch_label: len(fps)} if branch_label else {}
    return {
        "root": str(root),
        "file_count": len(fps),
        "truncated": truncated,
        "fingerprints": fps,
        "branches_seen": seen,
        "branch_counts": counts,
        "branches_truncated": False,
        "all_branch_names": seen,
    }


def _read_exact(fp, n: int) -> bytes:
    buf = bytearray()
    while len(buf) < n:
        chunk = fp.read(n - len(buf))
        if not chunk:
            break
        buf.extend(chunk)
    return bytes(buf)


def _sha1_blobs(root: Path, blob_ids: list[str]) -> dict[str, str]:
    """Map git blob id → hashlib.sha1(content).hexdigest()[:16] (working-tree compatible)."""
    wanted = list(dict.fromkeys(b for b in blob_ids if b))
    out: dict[str, str] = {}
    if not wanted:
        return out
    try:
        proc = subprocess.Popen(
            ["git", "-C", str(root), "cat-file", "--batch"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=git_env(),
        )
    except OSError:
        return out
    if proc.stdin is None or proc.stdout is None:
        proc.wait(timeout=5)
        return out
    try:
        for blob in wanted:
            proc.stdin.write(blob.encode("ascii") + b"\n")
            proc.stdin.flush()
            header = proc.stdout.readline()
            if not header:
                break
            parts = header.decode("ascii", "replace").strip().split()
            if len(parts) < 2 or parts[1] == "missing":
                continue
            try:
                size = int(parts[2])
            except (IndexError, ValueError):
                continue
            data = _read_exact(proc.stdout, size)
            proc.stdout.read(1)  # trailing newline after blob
            digest = hashlib.sha1(data).hexdigest()[:16]
            out[blob] = digest
    except OSError:
        pass
    finally:
        try:
            if proc.stdin is not None:
                proc.stdin.close()
        except OSError:
            pass
        try:
            proc.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            try:
                proc.kill()
                proc.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                pass
        try:
            if proc.stdout is not None:
                proc.stdout.close()
        except OSError:
            pass
    return out


def _iter_ls_tree(root: Path, ref: str) -> Iterator[tuple[str, str, str, int, str]]:
    raw = git_bytes(root, "ls-tree", "-r", "-l", "-z", ref, timeout=120)
    if not raw:
        return
    for rec in raw.split(b"\0"):
        if not rec:
            continue
        try:
            meta, path_b = rec.split(b"\t", 1)
        except ValueError:
            continue
        parts = meta.split()
        if len(parts) < 4:
            continue
        mode = parts[0].decode("ascii", "replace")
        typ = parts[1].decode("ascii", "replace")
        sha = parts[2].decode("ascii", "replace")
        try:
            size = int(parts[3].decode("ascii", "replace"))
        except ValueError:
            size = 0
        path = path_b.decode("utf-8", "surrogateescape").replace("\\", "/")
        yield mode, typ, sha, size, path


def scan_git_branches(
    root: Path,
    *,
    max_files: int = FINGERPRINT_CAP,
    max_bytes: int = MAX_FILE_BYTES,
    max_branches: int = DEFAULT_MAX_BRANCHES,
) -> dict[str, Any]:
    """Fingerprint files on every branch via ls-tree (no working-tree thrash)."""
    root = root.resolve()
    pairs, omitted, all_names = ordered_branch_refs(root, max_branches=max_branches)
    if not pairs:
        return scan_tree(root, max_files=max_files, max_bytes=max_bytes)

    tree_to_names: dict[str, list[str]] = {}
    tree_to_ref: dict[str, str] = {}
    for name, ref in pairs:
        tree = git_capture(root, "rev-parse", f"{ref}^{{tree}}", timeout=20)
        if not tree:
            continue
        tree_to_names.setdefault(tree, []).append(name)
        tree_to_ref.setdefault(tree, ref)

    if not tree_to_ref:
        return scan_tree(root, max_files=max_files, max_bytes=max_bytes)

    # (path, blob_sha) → size, branches
    collected: dict[tuple[str, str], dict[str, Any]] = {}
    branch_counts: dict[str, int] = {name: 0 for name, _ref in pairs}
    branch_truncated: dict[str, bool] = {name: False for name, _ref in pairs}

    for tree, names in tree_to_names.items():
        ref = tree_to_ref[tree]
        listed = 0
        hit_cap = False
        for mode, typ, sha, size, rel in _iter_ls_tree(root, ref):
            if typ != "blob" or mode == "120000":
                continue
            if should_skip_rel(rel):
                continue
            if size > max_bytes:
                continue
            listed += 1
            if listed > max_files:
                hit_cap = True
                break
            key = (rel, sha)
            entry = collected.get(key)
            if entry is None:
                collected[key] = {"path": rel, "blob": sha, "bytes": size, "branches": list(names)}
            else:
                for n in names:
                    if n not in entry["branches"]:
                        entry["branches"].append(n)
        for n in names:
            branch_counts[n] = branch_counts.get(n, 0) + min(listed, max_files)
            if hit_cap:
                branch_truncated[n] = True

    scanned_names = [n for names in tree_to_names.values() for n in names]
    branches_seen = [name for name, _ref in pairs if name in scanned_names] or [
        name for name, _ref in pairs
    ]

    items = list(collected.values())
    global_truncated = len(items) > max_files or any(branch_truncated.values())
    items = items[:max_files]

    blob_ids = [str(it["blob"]) for it in items]
    hashes = _sha1_blobs(root, blob_ids)

    fps: list[dict[str, Any]] = []
    # Dedup identical content hashes at the same path across branches (already
    # keyed by path+blob). Also collapse same sha1+path if cat-file aliases.
    seen_fp: dict[tuple[str, str], dict[str, Any]] = {}
    for it in items:
        rel = str(it["path"])
        digest = hashes.get(str(it["blob"])) or str(it["blob"])[:16]
        key = (rel, digest)
        existing = seen_fp.get(key)
        branches = list(it.get("branches") or [])
        if existing is not None:
            for b in branches:
                if b not in existing["seen_on_branches"]:
                    existing["seen_on_branches"].append(b)
            continue
        fp = {
            "path": rel,
            "sha1": digest,
            "bytes": int(it.get("bytes") or 0),
            "ext": Path(rel).suffix.lower(),
            "seen_on_branches": branches,
        }
        seen_fp[key] = fp
        fps.append(fp)

    truncated = global_truncated or len(collected) > max_files
    return {
        "root": str(root),
        "file_count": len(fps),
        "truncated": truncated,
        "fingerprints": fps,
        "branches_seen": branches_seen,
        "branch_counts": branch_counts,
        "branches_truncated": bool(omitted) or any(branch_truncated.values()),
        "all_branch_names": all_names,
        "branches_omitted": omitted,
        "per_branch_truncated": {k: v for k, v in branch_truncated.items() if v},
    }


def scan_source(
    root: Path,
    *,
    all_branches: bool = True,
    max_files: int = FINGERPRINT_CAP,
    max_bytes: int = MAX_FILE_BYTES,
    max_branches: int = DEFAULT_MAX_BRANCHES,
) -> dict[str, Any]:
    """Scan a resolved source: all git branches when possible, else the working tree."""
    root = root.resolve()
    if all_branches and is_git_work_tree(root):
        return scan_git_branches(
            root,
            max_files=max_files,
            max_bytes=max_bytes,
            max_branches=max_branches,
        )
    label = ""
    if is_git_work_tree(root):
        label = git_capture(root, "rev-parse", "--abbrev-ref", "HEAD") or "HEAD"
        if label == "HEAD":
            label = "HEAD"
    return scan_tree(
        root,
        max_files=max_files,
        max_bytes=max_bytes,
        branch_label=label,
    )
