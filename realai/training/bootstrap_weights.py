"""Install RealAI-branded weights from on-disk GGUF you already have (no F16/HF)."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from realai.model_assets import models_root, repo_root, resolve_realai_gguf

from .export_gguf import publish_gguf

# Dev/reference GGUF in repo root — used only to stand up native inference until trained weights exist.
_DEFAULT_SOURCES: Dict[str, str] = {
    "realai-1.0-instruct": "models/Llama-3.2-1B-Instruct-Q4_K_M.gguf",
    "realai-1.0": "models/Llama-3.2-1B-Instruct-Q4_K_M.gguf",
}


def _resolve_source(path_str: str) -> Optional[Path]:
    raw = Path(path_str).expanduser()
    if raw.is_file():
        return raw.resolve()
    for base in (repo_root(), models_root(), Path.cwd()):
        joined = (base / raw).resolve()
        if joined.is_file():
            return joined
    return None


def discover_local_gguf() -> List[Path]:
    root = models_root()
    found: List[Path] = []
    for pattern in ("*.gguf", "*/*.gguf"):
        found.extend(sorted(root.glob(pattern)))
    # De-dupe; skip anything already under realai-*/weights with branded name
    unique: List[Path] = []
    seen = set()
    for path in found:
        key = str(path.resolve())
        if key in seen:
            continue
        if "realai-" in path.parts and "weights" in path.parts:
            if path.name.startswith("realai-"):
                continue
        seen.add(key)
        unique.append(path.resolve())
    return unique


def bootstrap_native_weights(
    *,
    model_id: str = "realai-1.0-instruct",
    source: Optional[str] = None,
    quant: str = "Q4_K_M",
    copy_to: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Copy an existing quantized GGUF into models/<id>/weights/ with RealAI naming."""
    src_path: Optional[Path] = None
    if source:
        src_path = _resolve_source(source)
    if src_path is None:
        default = os.environ.get("REALAI_BOOTSTRAP_GGUF", "").strip() or _DEFAULT_SOURCES.get(
            model_id, _DEFAULT_SOURCES["realai-1.0-instruct"]
        )
        src_path = _resolve_source(default)
    if src_path is None:
        candidates = discover_local_gguf()
        if candidates:
            src_path = candidates[0]

    if src_path is None:
        return {
            "status": "no_source",
            "message": "No .gguf found. Place a file under models/ or set REALAI_BOOTSTRAP_GGUF.",
            "candidates_checked": list(_DEFAULT_SOURCES.values()),
        }

    extras = list(copy_to or [])
    if model_id == "realai-1.0-instruct" and "realai-1.0" not in extras:
        extras.append("realai-1.0")

    result = publish_gguf(
        src_path,
        model_id,
        quant_label=quant,
        copy_to=extras,
        metadata={
            "bootstrap": True,
            "bootstrap_source": str(src_path),
            "note": "Dev bootstrap from existing GGUF; replace with fine-tuned RealAI weights when ready.",
        },
    )
    result["bootstrap_source"] = str(src_path)
    return result


def ensure_native_weights_if_missing(
    model_id: str = "realai-1.0-instruct",
) -> Dict[str, Any]:
    """No-op when weights exist; otherwise run bootstrap from env/default GGUF."""
    gguf, _diag = resolve_realai_gguf(model_id)
    if gguf is not None:
        return {"status": "already_ready", "model_id": model_id, "gguf": str(gguf)}
    if os.environ.get("REALAI_AUTO_BOOTSTRAP", "").strip().lower() not in ("1", "true", "yes"):
        return {"status": "missing", "model_id": model_id, "hint": "Set REALAI_AUTO_BOOTSTRAP=1 or run bootstrap_weights"}
    return bootstrap_native_weights(model_id=model_id)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bootstrap RealAI native GGUF from files you already have")
    parser.add_argument("--model-id", default="realai-1.0-instruct")
    parser.add_argument("--source", default=None, help="Path to any .gguf (Q4/Q5 OK; F16 not required)")
    parser.add_argument("--quant", default="Q4_K_M", help="Label for output filename only when copying Q4/Q5")
    parser.add_argument("--list", action="store_true", help="List discoverable GGUF under models/")
    return parser


def main(argv: Optional[List[str]] = None) -> Dict[str, Any]:
    args = build_parser().parse_args(argv)
    if args.list:
        payload = {"discovered": [str(p) for p in discover_local_gguf()]}
        print(json.dumps(payload, indent=2))
        return payload
    print("[realai] Bootstrapping native weights. If you get a 'user-mapped section' error on Windows,")
    print("         stop the inference server (the terminal running `python -m realai.server.app`) first.")
    result = bootstrap_native_weights(model_id=args.model_id, source=args.source, quant=args.quant)
    print(json.dumps(result, indent=2, default=str))
    return result


if __name__ == "__main__":
    main()