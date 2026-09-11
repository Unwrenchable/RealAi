#!/usr/bin/env python3
"""Smoke: craft promote deep must run real scripts and leave artifacts."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("REALAI_HOME", str(ROOT))
os.environ.setdefault("REALAI_WORKSPACE", str(ROOT))
os.environ.setdefault("REALAI_ROOT", str(ROOT))
os.environ["REALAI_SELF_IMPROVE"] = "true"
sys.path.insert(0, str(ROOT))

from realai.cli.craft import TOOLS, plan_tools, tool_promote  # noqa: E402


def main() -> int:
    print("plan /promote deep ->", plan_tools("/promote deep"))
    print("plan /dispatch ->", plan_tools("/dispatch"))
    print("plan deep promote ->", plan_tools("deep promote nested gold"))

    r = tool_promote(mode="deep", force=False, dry_run=False)
    print("OK", r.get("ok"))
    print("SUMMARY", r.get("summary"))
    for a in r.get("actions") or []:
        print("ACTION:", a)
    arts = r.get("artifacts") or {}
    for k, v in arts.items():
        print(f"ART {k}: exists={v.get('exists')} bytes={v.get('bytes')}")

    plans = plan_tools("/promote deep")
    name, kw = plans[0]
    out2 = TOOLS[name](**kw)
    print("VIA_TOOLS", out2.get("ok"), out2.get("summary"))

    # required evidence
    required = [
        ROOT / "scan_results" / "DEEP_PROMOTE_MAP.md",
        ROOT / "scan_results" / "deep_promote_queue.json",
        ROOT / "scan_results" / "DEEP_PROMOTE_WIRE_LOG.json",
    ]
    missing = [str(p) for p in required if not p.is_file() or p.stat().st_size <= 0]
    if missing:
        print("MISSING", missing)
        return 1
    if not r.get("ok"):
        print("PROMOTE_NOT_OK", json.dumps({k: r.get(k) for k in ('error','steps')}, default=str)[:2000])
        return 2
    print("SMOKE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
