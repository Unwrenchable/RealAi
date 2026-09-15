"""
python -m realai.learn_git

Static git-learn pipeline. Never starts heal, GPU, or the orchestrator.

  python -m realai.learn_git <local-folder-OR-git-URL> [--write] [--refresh] [--all-branches] [--max-branches N] [--max-files N]

Local folder (kind: local):  python -m realai.learn_git C:\\path\\to\\folder
Git URL:                     python -m realai.learn_git https://github.com/org/repo
"""
from __future__ import annotations

import argparse
import json
import shlex
import sys
from typing import Any, Sequence

from realai.learn.pipeline import run_learn
from realai.learn.scan import DEFAULT_MAX_BRANCHES, FINGERPRINT_CAP

_SOURCE_HELP = (
    "Local folder OR git URL (Windows path, ./folder, owner/repo, or HTTPS). "
    "Real folders stay kind=local. Default: cwd"
)


def split_learn_rest(rest: str) -> list[str]:
    """Tokenize Craft ``/learn`` rest. Keep Windows drives; strip quotes; allow spaces."""
    raw = (rest or "").strip()
    if not raw:
        return []
    try:
        # posix=False so C:\\path\\to\\folder is not eaten by \\t / \\f escapes.
        tokens = shlex.split(raw, posix=False)
    except ValueError:
        tokens = raw.split()
    out: list[str] = []
    for t in tokens:
        s = str(t).strip()
        if len(s) >= 2 and s[0] == s[-1] and s[0] in {'"', "'"}:
            s = s[1:-1]
        if s:
            out.append(s)
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m realai.learn_git",
        description=(
            "Scan a local folder OR git URL across all branches, write a "
            "learning packet, optionally scaffold a coach plugin stub. "
            "Local folders that exist on disk stay kind=local (no clone). "
            "Does not start heal, GPU, or the orchestrator."
        ),
    )
    p.add_argument(
        "source",
        nargs="?",
        default=".",
        help=_SOURCE_HELP,
    )
    p.add_argument(
        "--write",
        action="store_true",
        help="Scaffold or upgrade realai/plugins/<slug>_coach/ from the packet",
    )
    p.add_argument(
        "--refresh",
        action="store_true",
        help="Wipe disposable clone cache for this slug before cloning",
    )
    p.add_argument(
        "--all-branches",
        dest="all_branches",
        action="store_true",
        default=True,
        help="Scan every git branch (default: on)",
    )
    p.add_argument(
        "--no-all-branches",
        dest="all_branches",
        action="store_false",
        help="Scan only the current checkout / default-branch working tree",
    )
    p.add_argument(
        "--max-branches",
        type=int,
        default=DEFAULT_MAX_BRANCHES,
        metavar="N",
        help=f"Cap branches scanned (default: {DEFAULT_MAX_BRANCHES})",
    )
    p.add_argument(
        "--max-files",
        type=int,
        default=FINGERPRINT_CAP,
        metavar="N",
        help=f"Cap unique file fingerprints (default: {FINGERPRINT_CAP})",
    )
    p.add_argument(
        "--json",
        action="store_true",
        default=True,
        help=argparse.SUPPRESS,
    )
    return p


def _coalesce_source_tokens(argv: list[str]) -> list[str]:
    """Join unquoted path pieces (Windows spaces) before argparse sees them."""
    flags: list[str] = []
    parts: list[str] = []
    i = 0
    takes_val = {"--max-branches", "--max-files"}
    while i < len(argv):
        t = str(argv[i])
        if t.startswith("-"):
            flags.append(t)
            if t in takes_val and i + 1 < len(argv) and not str(argv[i + 1]).startswith("-"):
                flags.append(str(argv[i + 1]))
                i += 2
                continue
            i += 1
            continue
        parts.append(t)
        i += 1
    if len(parts) > 1:
        return [" ".join(parts), *flags]
    return argv


def parse_learn_tokens(tokens: Sequence[str] | None) -> argparse.Namespace:
    """Parse learn CLI tokens (also used by Craft /learn). Never sys.exits."""
    argv = []
    for t in tokens or []:
        tl = str(t).lower()
        if tl == "write":
            argv.append("--write")
        elif tl == "refresh":
            argv.append("--refresh")
        else:
            argv.append(str(t))
    argv = _coalesce_source_tokens(argv)
    p = build_parser()
    p.exit_on_error = False
    try:
        ns = p.parse_args(argv)
        src = str(getattr(ns, "source", "") or "").strip()
        if len(src) >= 2 and src[0] == src[-1] and src[0] in {'"', "'"}:
            ns.source = src[1:-1]
        return ns
    except (argparse.ArgumentError, SystemExit):
        ns = p.parse_args([])
        # Best-effort: join leftover non-flag tokens (paths with spaces).
        parts = [t for t in argv if not str(t).startswith("-")]
        if parts:
            joined = " ".join(parts)
            if len(joined) >= 2 and joined[0] == joined[-1] and joined[0] in {'"', "'"}:
                joined = joined[1:-1]
            ns.source = joined
        ns.write = any(t.lower() in {"--write", "write"} for t in argv)
        ns.refresh = any(t.lower() in {"--refresh", "refresh"} for t in argv)
        return ns


def compact_learn_result(result: dict[str, Any]) -> dict[str, Any]:
    printable = dict(result)
    packet = printable.get("packet")
    if isinstance(packet, dict):
        fps = packet.get("fingerprints") or []
        printable["packet"] = {
            **{k: v for k, v in packet.items() if k != "fingerprints"},
            "fingerprint_count": len(fps) if isinstance(fps, list) else 0,
        }
    return printable


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    result: dict[str, Any] = run_learn(
        args.source,
        write=bool(args.write),
        refresh=bool(args.refresh),
        all_branches=bool(args.all_branches),
        max_branches=int(args.max_branches),
        max_files=int(args.max_files),
    )
    print(json.dumps(compact_learn_result(result), indent=2, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
