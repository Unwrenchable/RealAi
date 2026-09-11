#!/usr/bin/env python3
"""
Register / brand chat model id: realai-hive (display: RealAI Hive).

Points at the primary Vulkan GGUF (default: qwen2.5-coder-7b-instruct-q5_k_m.gguf).

  python scripts/register_realai_hive.py
  python scripts/register_realai_hive.py --gguf C:\\models\\checkpoints_lora\\qwen2.5-coder-7b-instruct-q5_k_m.gguf
  python scripts/register_realai_hive.py --set-default
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--gguf",
        default=os.environ.get(
            "REALAI_HIVE_GGUF",
            r"C:\models\checkpoints_lora\qwen2.5-coder-7b-instruct-q5_k_m.gguf",
        ),
    )
    ap.add_argument("--set-default", action="store_true", default=True)
    ap.add_argument("--no-set-default", action="store_true")
    args = ap.parse_args()
    if args.no_set_default:
        args.set_default = False

    gguf = Path(args.gguf)
    if not gguf.is_file():
        # try resolve by name
        from realai.model_catalog import _resolve_existing_gguf

        found = _resolve_existing_gguf(str(gguf))
        if not found:
            print(f"[hive] missing GGUF: {gguf}", file=sys.stderr)
            return 1
        gguf = found

    os.environ["REALAI_HIVE_GGUF"] = str(gguf)
    if args.set_default:
        os.environ["REALAI_DEFAULT_MODEL"] = "realai-hive"

    # Persist user env on Windows
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "REALAI_HIVE_GGUF", 0, winreg.REG_EXPAND_SZ, str(gguf))
        if args.set_default:
            winreg.SetValueEx(
                key, "REALAI_DEFAULT_MODEL", 0, winreg.REG_EXPAND_SZ, "realai-hive"
            )
        winreg.CloseKey(key)
        print("[hive] persisted REALAI_HIVE_GGUF (+ DEFAULT) to user env")
    except Exception as e:
        print(f"[hive] user-env persist skipped: {e}")

    # Branded weights dir + manifest
    brand = ROOT / "models" / "realai-hive"
    brand.mkdir(parents=True, exist_ok=True)
    weights = brand / "weights"
    weights.mkdir(exist_ok=True)
    # Junction/hardlink optional — store pointer file instead of copying 5GB
    pointer = brand / "ACTIVE_GGUF.txt"
    pointer.write_text(str(gguf), encoding="utf-8")
    manifest = {
        "id": "realai-hive",
        "display_name": "RealAI Hive",
        "owned_by": "realai",
        "family": "hive",
        "gguf": str(gguf),
        "gguf_filename": gguf.name,
        "backend": "llama.cpp-vulkan",
        "capabilities": ["chat", "completion", "coding", "hive", "organs"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "notes": [
            "Flagship branded id for craft /model RealAI Hive",
            "Vulkan serves one GGUF at a time — restart llama-server with this path to hot-load",
            "Organs/hive abilities use the same chat backend via orchestrator",
        ],
    }
    (brand / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    from realai.model_catalog import build_catalog, resolve_model_for_backend

    cat = build_catalog()
    ids = [m.get("id") for m in cat.get("data") or []]
    backend, meta = resolve_model_for_backend("RealAI Hive")
    print(f"[hive] registered id=realai-hive")
    print(f"[hive] gguf={gguf}")
    print(f"[hive] catalog has realai-hive: {'realai-hive' in ids}")
    print(f"[hive] resolve('RealAI Hive') → {meta.get('resolved_id')} backend={backend}")
    print(f"[hive] default_model={((cat.get('realai') or {}).get('default_model'))}")
    print(f"[hive] manifest → {brand / 'manifest.json'}")
    print()
    print("Craft:  /model RealAI Hive")
    print("Chat:   ensure Vulkan loaded with the hive GGUF, then:")
    print(f'  C:\\llama-vulkan\\llama-server.exe -m "{gguf}" --host 0.0.0.0 --port 8080 -c 16384 -ngl 99 --jinja')
    print("  or: powershell -File scripts\\run_local_chat.ps1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
