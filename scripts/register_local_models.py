#!/usr/bin/env python3
"""Scan C:\\models\\checkpoints_lora and persist RealAI model registry."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "realai")]

from realai.models.model_catalog import (  # noqa: E402
    _MODELS_DIR,
    _REGISTRY,
    _iter_ggufs,
    build_catalog,
)


def main() -> int:
    scanned = _iter_ggufs(_MODELS_DIR)
    print(f"scanned_ggufs={len(scanned)} dir={_MODELS_DIR}")
    for p in scanned:
        try:
            rel = p.relative_to(_MODELS_DIR)
        except Exception:
            rel = p
        print(f"  {rel}")

    cat = build_catalog()
    data = [m for m in (cat.get("data") or []) if isinstance(m, dict)]
    print(f"catalog_count={len(data)} registry={_REGISTRY}")

    gguf_models = []
    for m in data:
        meta = m.get("realai") or {}
        if meta.get("gguf_filename"):
            gguf_models.append(m)
            print(
                f"  {m.get('id'):28} {meta.get('gguf_filename')} "
                f"loaded={meta.get('loaded_now')}"
            )

    product = ROOT / "config" / "realai_models.json"
    pkg = _REGISTRY
    for path in (pkg, product):
        if path.is_file():
            payload = json.loads(path.read_text(encoding="utf-8"))
            print(f"saved {path} entries={len(payload.get('models') or [])}")

    ids = {m.get("id") for m in data}
    for need in ("local-qwen3-27b", "realai-lora-1.5b", "local-llama-1b", "realai-hive"):
        print(f"has {need}={need in ids}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
