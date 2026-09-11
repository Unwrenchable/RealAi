#!/usr/bin/env python3
"""
One command: LoRA train → merge HF → convert GGUF → quantize → swap into Vulkan chat path.

Default target: qwen-coder-7b (your chat GGUF).

  python scripts/train_to_chat_gguf.py
  python scripts/train_to_chat_gguf.py --preset qwen-coder-7b --max-steps 30
  python scripts/train_to_chat_gguf.py --preset qwen-1.5b --max-steps 50
  python scripts/train_to_chat_gguf.py --skip-train   # merge+export existing adapter only
  python scripts/train_to_chat_gguf.py --dry-run

Flow:
  1) pause Vulkan (free AMD VRAM)
  2) DirectML LoRA train (unless --skip-train)
  3) merge adapter into HF base on CPU
  4) convert_hf_to_gguf.py → f16/q8 intermediate
  5) llama-quantize.exe → Q5_K_M (or --quant)
  6) backup + swap chat GGUF
  7) optional --restart-chat
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PRESETS = ROOT / "config" / "train_presets.json"
CKPT = Path(os.environ.get("TRAIN_OUTPUT_DIR") or r"C:\models\checkpoints_lora")
REPORT = ROOT / "scan_results" / "TRAIN_TO_CHAT_GGUF.json"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(msg: str) -> None:
    print(f"[train→gguf] {msg}", flush=True)


def load_preset(name: str) -> Dict[str, Any]:
    data = json.loads(PRESETS.read_text(encoding="utf-8"))
    presets = data.get("presets") or {}
    if name not in presets:
        raise SystemExit(f"Unknown preset {name!r}. Known: {', '.join(sorted(presets))}")
    return presets[name]


def run(cmd: list[str], timeout: int = 0) -> None:
    log("RUN " + " ".join(cmd))
    kwargs: Dict[str, Any] = {
        "cwd": str(ROOT),
        "check": True,
    }
    if timeout > 0:
        kwargs["timeout"] = timeout
    subprocess.run(cmd, **kwargs)


def ensure_directml_path() -> None:
    dml = os.environ.get("REALAI_DIRECTML_DIR") or r"C:\DirectML\runtime\x64"
    if Path(dml).is_dir():
        os.environ["REALAI_DIRECTML_DIR"] = dml
        os.environ["PATH"] = dml + os.pathsep + os.environ.get("PATH", "")


def pause_vulkan() -> None:
    for name in ("llama-server.exe", "llama-server"):
        subprocess.run(["taskkill", "/IM", name, "/F"], capture_output=True, text=True)
    log("paused Vulkan llama-server (if it was running)")


def merge_adapter(base_model: str, adapter_dir: Path, merged_dir: Path) -> Path:
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    log(f"merge LoRA on CPU: base={base_model} adapter={adapter_dir}")
    merged_dir.mkdir(parents=True, exist_ok=True)
    tok = AutoTokenizer.from_pretrained(str(adapter_dir), trust_remote_code=True)
    # Prefer tokenizer from adapter (saved during train); fallback to base
    if tok.pad_token is None:
        tok = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
        if tok.pad_token is None:
            tok.pad_token = tok.eos_token

    base = AutoModelForCausalLM.from_pretrained(
        base_model,
        trust_remote_code=True,
        torch_dtype=torch.float16,
        low_cpu_mem_usage=True,
        device_map="cpu",
    )
    model = PeftModel.from_pretrained(base, str(adapter_dir))
    merged = model.merge_and_unload()
    merged.save_pretrained(str(merged_dir), safe_serialization=True)
    tok.save_pretrained(str(merged_dir))
    meta = {
        "base_model": base_model,
        "adapter": str(adapter_dir),
        "merged_at": utc(),
    }
    (merged_dir / "realai_merge_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log(f"merged → {merged_dir}")
    return merged_dir


def convert_to_gguf(merged_dir: Path, out_gguf: Path) -> Path:
    from realai.training.llama_tools import find_convert_hf_script, python_for_llama_convert

    convert = find_convert_hf_script()
    if not convert:
        raise FileNotFoundError(
            "convert_hf_to_gguf.py not found. Set REALAI_LLAMA_CPP_ROOT to a llama.cpp checkout "
            "(found default search includes C:\\Users\\<you>\\llama.cpp)."
        )
    out_gguf.parent.mkdir(parents=True, exist_ok=True)
    # Prefer outfile next to merged; many convert scripts accept --outfile
    py = python_for_llama_convert()
    cmd = [
        py,
        str(convert),
        str(merged_dir),
        "--outfile",
        str(out_gguf),
        "--outtype",
        "f16",
    ]
    log("converting HF → GGUF f16 (slow for 7B)…")
    try:
        run(cmd)
    except subprocess.CalledProcessError:
        # older CLI variants
        cmd2 = [py, str(convert), str(merged_dir), "--outtype", "f16"]
        run(cmd2)
        # find produced gguf beside merged_dir
        produced = list(merged_dir.glob("*.gguf")) + list(merged_dir.parent.glob("*.gguf"))
        if not produced:
            raise FileNotFoundError("convert finished but no .gguf found")
        produced.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        shutil.copy2(produced[0], out_gguf)
    if not out_gguf.is_file():
        raise FileNotFoundError(f"expected GGUF missing: {out_gguf}")
    return out_gguf


def quantize_gguf(src_f16: Path, dest_q: Path, quant: str) -> Path:
    from realai.training.llama_tools import find_llama_quantize

    quant_bin = find_llama_quantize()
    if not quant_bin:
        # explicit fallback
        cand = Path(r"C:\llama-vulkan\llama-quantize.exe")
        if cand.is_file():
            quant_bin = cand
    if not quant_bin:
        raise FileNotFoundError("llama-quantize.exe not found (expected under C:\\llama-vulkan)")

    dest_q.parent.mkdir(parents=True, exist_ok=True)
    # llama-quantize usage: llama-quantize input.gguf output.gguf Q5_K_M
    run([str(quant_bin), str(src_f16), str(dest_q), quant])
    if not dest_q.is_file():
        raise FileNotFoundError(f"quantize produced no file: {dest_q}")
    return dest_q


def swap_chat_gguf(new_gguf: Path, chat_gguf: Path) -> Dict[str, Any]:
    pause_vulkan()
    chat_gguf = chat_gguf.resolve()
    new_gguf = new_gguf.resolve()
    chat_gguf.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if chat_gguf.is_file():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = chat_gguf.with_name(chat_gguf.stem + f".bak_{stamp}" + chat_gguf.suffix)
        # rename aside (may fail if mapped — we already killed server)
        try:
            chat_gguf.replace(backup)
        except OSError:
            shutil.copy2(chat_gguf, backup)
            chat_gguf.unlink(missing_ok=True)
        log(f"backed up old chat GGUF → {backup}")
    tmp = chat_gguf.with_suffix(chat_gguf.suffix + ".tmp")
    shutil.copy2(new_gguf, tmp)
    os.replace(tmp, chat_gguf)
    log(f"swapped chat GGUF → {chat_gguf}")
    return {"chat_gguf": str(chat_gguf), "backup": str(backup) if backup else None, "source": str(new_gguf)}


def restart_chat() -> None:
    ps1 = ROOT / "scripts" / "run_local_chat.ps1"
    shell = "pwsh" if shutil.which("pwsh") else "powershell"
    log("restarting chat stack (Vulkan + orch)…")
    subprocess.Popen(
        [shell, "-ExecutionPolicy", "Bypass", "-File", str(ps1), "-SkipUI", "-SkipPromote"],
        cwd=str(ROOT),
    )


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="One command: train LoRA → GGUF → swap into Vulkan chat")
    ap.add_argument("--preset", default="qwen-coder-7b")
    ap.add_argument("--device", default=os.environ.get("REALAI_TRAIN_DEVICE") or "directml")
    ap.add_argument("--max-steps", type=int, default=0, help="0 = use preset default")
    ap.add_argument("--quant", default="Q5_K_M")
    ap.add_argument("--skip-train", action="store_true", help="Use existing adapter; merge+export only")
    ap.add_argument("--skip-swap", action="store_true", help="Build GGUF but do not replace chat file")
    ap.add_argument("--restart-chat", action="store_true", help="Start run_local_chat.ps1 after swap")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--keep-f16", action="store_true", help="Keep intermediate f16 GGUF")
    args = ap.parse_args(argv)

    ensure_directml_path()
    preset = load_preset(args.preset)
    base = preset["hf_model"]
    adapter_subdir = preset["adapter_subdir"]
    chat_gguf = Path(preset.get("chat_gguf") or "")
    if not chat_gguf:
        raise SystemExit(f"Preset {args.preset} has no chat_gguf path to swap into")

    steps = args.max_steps or int(preset.get("max_steps_default") or 30)
    adapter_dir = CKPT / adapter_subdir
    work = CKPT / f"{adapter_subdir}-export"
    merged_dir = work / "merged"
    f16_gguf = work / f"{adapter_subdir}-f16.gguf"
    q_gguf = work / f"{adapter_subdir}-{args.quant}.gguf"

    plan = {
        "preset": args.preset,
        "base_model": base,
        "adapter_dir": str(adapter_dir),
        "merged_dir": str(merged_dir),
        "f16_gguf": str(f16_gguf),
        "quant_gguf": str(q_gguf),
        "chat_gguf": str(chat_gguf),
        "max_steps": steps,
        "device": args.device,
        "quant": args.quant,
        "skip_train": args.skip_train,
    }
    log(json.dumps(plan, indent=2))
    if args.dry_run:
        log("dry-run only — nothing executed")
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps({"dry_run": True, **plan, "at": utc()}, indent=2), encoding="utf-8")
        return 0

    result: Dict[str, Any] = {"at": utc(), "plan": plan, "ok": False}

    try:
        pause_vulkan()

        if not args.skip_train:
            train_cmd = [
                sys.executable,
                "-u",
                str(ROOT / "scripts" / "train_lora_local.py"),
                "--preset",
                args.preset,
                "--device",
                args.device,
                "--max-steps",
                str(steps),
                "--adapter-subdir",
                adapter_subdir,
                "--keep-vulkan",  # already paused here
            ]
            # force vram-safe via defaults inside trainer
            run(train_cmd)
        else:
            if not (adapter_dir / "adapter_config.json").is_file():
                raise FileNotFoundError(f"No adapter at {adapter_dir} — run without --skip-train first")
            log(f"skip-train: using existing adapter {adapter_dir}")

        merge_adapter(base, adapter_dir, merged_dir)
        convert_to_gguf(merged_dir, f16_gguf)
        quantize_gguf(f16_gguf, q_gguf, args.quant)

        swap_info = None
        if not args.skip_swap:
            swap_info = swap_chat_gguf(q_gguf, chat_gguf)
        else:
            log(f"skip-swap: quantized GGUF ready at {q_gguf}")

        if not args.keep_f16 and f16_gguf.is_file():
            try:
                f16_gguf.unlink()
                log("removed intermediate f16 to save disk")
            except OSError:
                pass

        if args.restart_chat:
            restart_chat()

        result.update({"ok": True, "swap": swap_info, "quant_gguf": str(q_gguf)})
        log("DONE")
        if swap_info:
            log(f"Chat GGUF updated: {chat_gguf}")
            log("Restart chat if not using --restart-chat: powershell -File scripts\\run_local_chat.ps1")
    except Exception as e:
        result["ok"] = False
        result["error"] = f"{type(e).__name__}: {e}"
        log(f"FAILED: {result['error']}")
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return 1

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2), encoding="utf-8")
    log(f"report → {REPORT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
