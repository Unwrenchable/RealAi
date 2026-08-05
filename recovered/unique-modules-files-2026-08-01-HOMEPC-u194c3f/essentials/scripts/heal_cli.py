#!/usr/bin/env python3
"""CLI helpers for PowerShell self-heal (avoids quoting hell)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# Ensure repo root on path
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
os.environ.setdefault("REALAI_SELF_IMPROVE", "true")
os.chdir(_ROOT)


def _print(obj) -> None:
    try:
        print(json.dumps(obj, default=str, indent=2)[:4000])
    except Exception:
        print(obj)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "usage: heal_cli.py <learn|discover|assemble|promote|cycle|deepen|status> [args]",
            file=sys.stderr,
        )
        return 2
    cmd = argv[1].lower()

    if cmd == "learn":
        from realai.self_heal import run_learn_keywords
        r = run_learn_keywords()
        print("ok=", r.get("ok"))
        return 0 if r.get("ok") else 1

    if cmd == "discover":
        mode = argv[2] if len(argv) > 2 else "desktop"
        from realai.self_heal import run_discover
        r = run_discover(mode=mode)
        print("ok=", r.get("ok"), "mode=", mode, "keys=", list((r.get("results") or {}).keys()))
        return 0 if r.get("ok") else 1

    if cmd == "assemble":
        from realai.self_heal import run_assemble
        r = run_assemble()
        print("ok=", r.get("ok"))
        return 0 if r.get("ok") else 1

    if cmd == "promote":
        apply = "--apply" in argv or (len(argv) > 2 and argv[2] in ("1", "true", "apply"))
        from realai.self_heal import run_promote
        r = run_promote(apply=apply)
        print("ok=", r.get("ok"), "apply=", apply)
        return 0 if r.get("ok") else 1

    if cmd == "cycle":
        apply = "--apply" in argv or (len(argv) > 2 and argv[2] in ("1", "true", "apply"))
        from realai.self_heal import run_full_cycle
        r = run_full_cycle(apply_promote=apply)
        print("steps=", len(r.get("steps") or []), "keys=", list(r.keys())[:12])
        return 0

    if cmd == "deepen":
        from realai.deepen_cycle import run_deepen
        r = run_deepen(assemble=True, hive=True, cycle=True)
        print(
            "deeper=", r.get("deeper"),
            "score", r.get("before_score"), "->", r.get("after_score"),
            "success=", r.get("success"),
        )
        return 0 if r.get("success") else 1

    if cmd == "status":
        from realai.self_heal import status
        _print(status())
        return 0

    print("unknown command:", cmd, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
