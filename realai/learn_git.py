"""
python -m realai.learn_git

Static git-learn pipeline. Never starts heal, GPU, or the orchestrator.

  python -m realai.learn_git <src> [--write] [--refresh] [--all-branches] [--max-branches N] [--max-files N]
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Sequence

from realai.learn.pipeline import run_learn
from realai.learn.scan import DEFAULT_MAX_BRANCHES, FINGERPRINT_CAP


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m realai.learn_git",
        description=(
            "Scan a git source (local path, owner/repo, or HTTPS URL) across "
            "all branches, write a learning packet, optionally scaffold a coach "
            "plugin stub. Does not start heal, GPU, or the orchestrator."
        ),
    )
    p.add_argument(
        "source",
        nargs="?",
        default=".",
        help="Local path, owner/repo, or HTTPS git URL (default: cwd)",
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
    p = build_parser()
    p.exit_on_error = False
    try:
        return p.parse_args(argv)
    except (argparse.ArgumentError, SystemExit):
        ns = p.parse_args([])
        # Best-effort: treat remaining non-flag tokens as source.
        parts = [t for t in argv if not t.startswith("-")]
        if parts:
            ns.source = " ".join(parts)
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
