#!/usr/bin/env python3
"""Shim: nested root walk lives in tools/walk_root.py (craft resolves either)."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "tools" / "walk_root.py"

if not TARGET.is_file():
    print(f"[walk_root] missing {TARGET}", file=sys.stderr)
    raise SystemExit(1)

# Re-exec the tools implementation with the same argv
sys.argv[0] = str(TARGET)
runpy.run_path(str(TARGET), run_name="__main__")
