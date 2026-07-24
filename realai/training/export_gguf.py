"""Quantize and publish RealAI-branded GGUF weights under models/<id>/weights/."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from realai.model_assets import models_root, resolve_realai_gguf

from .llama_tools import find_convert_hf_script, find_llama_quantize, python_for_llama_convert


def _safe_copy_gguf(src: Path, dst: Path) -> None:
    """Copy a GGUF safely, with good error messages on Windows when the file is memory-mapped by a running server."""
    src = src.resolve()
    dst = dst.resolve()

    if src == dst:
        return

    dst.parent.mkdir(parents=True, exist_ok=True)

    tmp = dst.with_name(dst.name + ".tmp")

    try:
        shutil.copy2(src, tmp)
        os.replace(tmp, dst)  # atomic replace where possible
    except OSError as exc:
        # Clean up temp if left behind
        if tmp.exists():
            tmp.unlink(missing_ok=True)

        # Windows-specific "file is memory-mapped" (common when llama.cpp server has the GGUF loaded)
        if getattr(exc, "winerror", None) == 1224 or "user-mapped" in str(exc).lower():
            raise RuntimeError(
                "Cannot publish GGUF because the target (or source) file is currently memory-mapped.\n"
                "Your RealAI server (or any llama-cli / llama.cpp process) is holding the file open.\n\n"
                "Fix: Stop the inference server first (Ctrl+C in the terminal running\n"
                "     `python -m realai.server.app` or the background server),\n"
                "     then re-run this bootstrap / export command.\n\n"
                f"Source: {src}\nTarget: {dst}"
            ) from exc
        raise
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def default_output_name(model_id: str, quant: str) -> str:
    safe_quant = quant.replace(" ", "_")
    return f"{model_id}-{safe_quant}.gguf"


def source_is_prequantized(path: Path) -> bool:
    """True when the file is already a llama.cpp quant (do not run llama-quantize on it)."""
    name = path.name.upper()
    markers = (
        "Q4_K_M",
        "Q4_K_S",
        "Q5_K_M",
        "Q5_K_S",
        "Q6_K",
        "Q8_0",
        "Q3_K",
        "Q2_K",
        "IQ4",
    )
    return any(m in name for m in markers)


def weights_dir_for(model_id: str) -> Path:
    path = models_root() / model_id / "weights"
    path.mkdir(parents=True, exist_ok=True)
    return path


def publish_gguf(
    source_gguf: Path,
    model_id: str,
    *,
    quant_label: str = "Q4_K_M",
    copy_to: Optional[list[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Copy or quantize into the canonical RealAI weights layout."""
    source = source_gguf.expanduser().resolve()
    if not source.is_file() or source.suffix.lower() != ".gguf":
        raise FileNotFoundError(f"GGUF source not found: {source}")

    dest_name = default_output_name(model_id, quant_label)
    primary_dir = weights_dir_for(model_id)
    dest = primary_dir / dest_name

    # Fast path for the common bootstrap case (copying an already-quantized dev GGUF
    # into the branded realai-* location). If the destination already has an identical file,
    # we skip the copy entirely. This also avoids the "file is memory-mapped" error
    # when the server is running the *old* copy of the branded file.
    if dest.exists() and dest.stat().st_size == source.stat().st_size:
        pass  # already published at the correct location
    else:
        # --- actual publish work (copy or quantize) ---
        quantize_bin = find_llama_quantize()
        needs_quantize = (
            quantize_bin
            and quant_label
            and not source.name.endswith(f"-{quant_label}.gguf")
            and not source_is_prequantized(source)
        )
        if needs_quantize:
            tmp_f16 = primary_dir / f".{model_id}-f16-tmp.gguf"
            if source != dest:
                _safe_copy_gguf(source, tmp_f16)
            else:
                tmp_f16 = source
            try:
                subprocess.run(
                    [str(quantize_bin), str(tmp_f16), str(dest), quant_label],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            finally:
                if tmp_f16 != source and tmp_f16.exists():
                    tmp_f16.unlink(missing_ok=True)
        else:
            _safe_copy_gguf(source, dest)

    published = [str(dest)]
    for extra_id in copy_to or []:
        extra_dir = weights_dir_for(extra_id)
        extra_path = extra_dir / dest_name
        if extra_path.resolve() != dest.resolve():
            _safe_copy_gguf(dest, extra_path)
        published.append(str(extra_path))

    artifact = {
        "model_id": model_id,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "gguf": dest.name,
        "paths": published,
        "quant": quant_label,
        "source": str(source),
        **(metadata or {}),
    }
    (primary_dir / "artifact.json").write_text(json.dumps(artifact, indent=2), encoding="utf-8")

    gguf, diag = resolve_realai_gguf(model_id)
    return {
        "status": "published",
        "model_id": model_id,
        "gguf": str(dest),
        "registry_ready": gguf is not None,
        "diagnostics": diag,
        "artifact": artifact,
    }


def convert_hf_to_gguf(hf_dir: Path, out_f16: Path) -> Path:
    script = find_convert_hf_script()
    if not script:
        raise RuntimeError(
            "convert_hf_to_gguf.py not found. Clone llama.cpp and set REALAI_LLAMA_CPP_ROOT."
        )
    hf_dir = hf_dir.expanduser().resolve()
    if not hf_dir.is_dir():
        raise FileNotFoundError(f"HF checkpoint directory missing: {hf_dir}")
    out_f16.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [python_for_llama_convert(), str(script), str(hf_dir), "--outfile", str(out_f16), "--outtype", "f16"],
        check=True,
    )
    if not out_f16.is_file():
        raise RuntimeError(f"HF conversion did not produce {out_f16}")
    return out_f16


def export_from_hf(
    hf_dir: Path,
    model_id: str,
    *,
    quant: str = "Q4_K_M",
    copy_to: Optional[list[str]] = None,
) -> Dict[str, Any]:
    work = weights_dir_for(model_id)
    f16 = work / f".{model_id}-f16.gguf"
    convert_hf_to_gguf(hf_dir, f16)
    try:
        return publish_gguf(
            f16,
            model_id,
            quant_label=quant,
            copy_to=copy_to,
            metadata={"export_path": "hf", "hf_dir": str(hf_dir)},
        )
    finally:
        if f16.exists():
            f16.unlink(missing_ok=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Publish RealAI native GGUF weights")
    parser.add_argument("--model-id", default="realai-1.0-instruct")
    parser.add_argument("--gguf", help="Existing GGUF to quantize/copy into weights/")
    parser.add_argument("--hf-dir", help="HuggingFace merge dir to convert then quantize")
    parser.add_argument("--quant", default="Q4_K_M")
    parser.add_argument(
        "--also-copy-to",
        action="append",
        default=[],
        help="Additional model ids to receive the same file (e.g. realai-1.0)",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> Dict[str, Any]:
    args = build_parser().parse_args(argv)
    copy_to = list(args.also_copy_to)
    if args.model_id == "realai-1.0-instruct" and "realai-1.0" not in copy_to:
        copy_to.append("realai-1.0")

    if args.hf_dir:
        return export_from_hf(Path(args.hf_dir), args.model_id, quant=args.quant, copy_to=copy_to)
    if args.gguf:
        return publish_gguf(
            Path(args.gguf),
            args.model_id,
            quant_label=args.quant,
            copy_to=copy_to,
            metadata={"export_path": "gguf"},
        )
    raise SystemExit("Provide --gguf or --hf-dir")


if __name__ == "__main__":
    result = main()
    print(json.dumps(result, indent=2))