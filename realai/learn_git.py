"""
python -m realai.learn_git

Static git-learn pipeline. Never starts heal, GPU, or the orchestrator.

  python -m realai.learn_git .
  python -m realai.learn_git owner/repo
  python -m realai.learn_git https://github.com/acme/app.git --write
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from realai.learn.pipeline import run_learn


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m realai.learn_git",
        description=(
            "Scan a git source (local path, owner/repo, or HTTPS URL), "
            "write a learning packet, optionally scaffold a coach plugin stub. "
            "Does not start heal, GPU, or the orchestrator."
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
        "--json",
        action="store_true",
        default=True,
        help=argparse.SUPPRESS,
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    result: dict[str, Any] = run_learn(
        args.source,
        write=bool(args.write),
        refresh=bool(args.refresh),
    )
    # Keep packet fingerprints in the file; print a compact view on stdout.
    printable = dict(result)
    packet = printable.get("packet")
    if isinstance(packet, dict):
        fps = packet.get("fingerprints") or []
        printable["packet"] = {
            **{k: v for k, v in packet.items() if k != "fingerprints"},
            "fingerprint_count": len(fps) if isinstance(fps, list) else 0,
        }
    print(json.dumps(printable, indent=2, default=str))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
