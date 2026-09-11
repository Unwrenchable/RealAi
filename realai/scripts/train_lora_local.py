#!/usr/bin/env python3
"""
Portable LoRA fine-tune for RealAI users (AMD / NVIDIA / CPU).

Device order (override with REALAI_TRAIN_DEVICE=directml|cuda|cpu):
  1) DirectML  — AMD Windows GPU train (torch-directml)
  2) CUDA      — NVIDIA
  3) CPU       — always works (slower)

Vulkan llama-server is for INFERENCE only (chat/GGUF), not HF LoRA training.

Dataset (from scripts/wire_training.py):
  C:\\models\\checkpoints_lora\\normalized_datasets\\realai_lora_ready.jsonl

  python scripts/train_lora_local.py --max-steps 40
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from itertools import cycle
from pathlib import Path
from typing import Any, Tuple

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import torch
from torch.utils.data import DataLoader, Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model


class JsonlTextDataset(Dataset):
    def __init__(self, path: Path, tokenizer, max_length: int):
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.samples = []
        with path.open(encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                text = (obj.get("text") or "").strip()
                if text:
                    self.samples.append(text)
        if not self.samples:
            raise ValueError(f"No text rows in {path}")
        print(f"[train] loaded {len(self.samples)} samples from {path}", flush=True)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        text = self.samples[idx]
        enc = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )
        input_ids = enc["input_ids"].squeeze(0)
        attention_mask = enc["attention_mask"].squeeze(0)
        labels = input_ids.clone()
        labels[attention_mask == 0] = -100
        if self.tokenizer.pad_token_id is not None:
            labels[input_ids == self.tokenizer.pad_token_id] = -100
        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "labels": labels,
        }


def pick_device(prefer: str = "") -> Tuple[Any, str]:
    """
    Returns (torch.device or DirectML device, backend_name).
    prefer: '', 'directml', 'cuda', 'cpu'
    """
    prefer = (prefer or os.environ.get("REALAI_TRAIN_DEVICE") or "").strip().lower()

    def try_directml():
        try:
            import torch_directml

            # Probe that native DLL actually loads + device exists
            n = int(torch_directml.device_count())
            if n <= 0:
                return None
            dev = torch_directml.device()
            # tiny tensor probe
            t = torch.zeros(1, device=dev)
            _ = float(t.cpu().item())
            return dev, "directml"
        except Exception as e:
            print(f"[train] DirectML unavailable ({type(e).__name__}: {e})", flush=True)
            return None

    order = []
    if prefer in {"directml", "dml", "amd"}:
        order = ["directml", "cuda", "cpu"]
    elif prefer in {"cuda", "gpu-nvidia"}:
        order = ["cuda", "directml", "cpu"]
    elif prefer in {"cpu"}:
        order = ["cpu"]
    else:
        # Auto: AMD-friendly first on Windows, then CUDA, then CPU
        if sys.platform.startswith("win"):
            order = ["directml", "cuda", "cpu"]
        else:
            order = ["cuda", "cpu"]

    for name in order:
        if name == "directml":
            hit = try_directml()
            if hit:
                print(f"[train] device=directml (AMD/Windows)", flush=True)
                return hit
        elif name == "cuda":
            if torch.cuda.is_available():
                print(f"[train] device=cuda ({torch.cuda.get_device_name(0)})", flush=True)
                return torch.device("cuda"), "cuda"
        elif name == "cpu":
            print("[train] device=cpu (portable fallback — works for all users)", flush=True)
            return torch.device("cpu"), "cpu"

    return torch.device("cpu"), "cpu"


def _load_preset(name: str) -> dict:
    presets_path = Path(__file__).resolve().parents[1] / "config" / "train_presets.json"
    data = json.loads(presets_path.read_text(encoding="utf-8"))
    presets = data.get("presets") or {}
    if name not in presets:
        known = ", ".join(sorted(presets.keys())) or "(none)"
        raise SystemExit(f"Unknown preset {name!r}. Known: {known}")
    return presets[name]


def _port_up(port: int) -> bool:
    import socket

    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def _pause_vulkan_stack() -> list[str]:
    """Stop llama-server / free VRAM so DirectML can train on the same AMD GPU."""
    stopped: list[str] = []
    try:
        import subprocess

        # Prefer taskkill by image name (Windows)
        for name in ("llama-server.exe", "llama-server"):
            r = subprocess.run(
                ["taskkill", "/IM", name, "/F"],
                capture_output=True,
                text=True,
            )
            if r.returncode == 0 or "SUCCESS" in (r.stdout or "").upper():
                stopped.append(name)
        # Also free orch if user wants full VRAM (optional — only if env set)
        if os.environ.get("REALAI_TRAIN_STOP_ORCH", "").lower() in {"1", "true", "yes"}:
            # Don't kill arbitrary python; leave orch unless explicitly requested later
            pass
    except Exception as e:
        print(f"[train] pause-vulkan warning: {e}", flush=True)
    return stopped


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Portable RealAI LoRA trainer (DirectML/CUDA/CPU)")
    ap.add_argument(
        "--preset",
        default="",
        help="qwen-0.5b | qwen-coder-1.5b | qwen-coder-7b | llama-3.2-1b (from config/train_presets.json)",
    )
    ap.add_argument("--model", default=os.environ.get("TRAIN_MODEL_NAME", "Qwen/Qwen2.5-1.5B-Instruct"))
    ap.add_argument(
        "--dataset",
        default=os.environ.get(
            "TRAIN_DATASET_PATH",
            r"C:\models\checkpoints_lora\normalized_datasets\realai_lora_ready.jsonl",
        ),
    )
    ap.add_argument(
        "--output-dir",
        default=os.environ.get("TRAIN_OUTPUT_DIR", r"C:\models\checkpoints_lora"),
    )
    ap.add_argument(
        "--adapter-subdir",
        default=os.environ.get("TRAIN_ADAPTER_SUBDIR", "qwen2.5-1.5b-lora-realai"),
    )
    ap.add_argument("--max-steps", type=int, default=int(os.environ.get("TRAIN_MAX_STEPS", "40")))
    ap.add_argument("--batch-size", type=int, default=int(os.environ.get("TRAIN_BATCH_SIZE", "1")))
    ap.add_argument("--max-length", type=int, default=int(os.environ.get("TRAIN_MAX_LENGTH", "256")))
    ap.add_argument("--lr", type=float, default=float(os.environ.get("TRAIN_LR", "2e-4")))
    ap.add_argument("--lora-r", type=int, default=int(os.environ.get("TRAIN_LORA_R", "16")))
    ap.add_argument(
        "--device",
        default=os.environ.get("REALAI_TRAIN_DEVICE", ""),
        help="directml | cuda | cpu | auto(default)",
    )
    ap.add_argument(
        "--vram-safe",
        action="store_true",
        default=os.environ.get("REALAI_TRAIN_VRAM_SAFE", "1") not in {"0", "false", "no"},
        help="Shorter seq / smaller LoRA r for 12GB AMD (default ON)",
    )
    ap.add_argument(
        "--no-vram-safe",
        action="store_true",
        help="Disable vram-safe defaults",
    )
    ap.add_argument(
        "--pause-vulkan",
        action="store_true",
        default=True,
        help="Stop llama-server before DirectML train to free VRAM (default ON)",
    )
    ap.add_argument(
        "--keep-vulkan",
        action="store_true",
        help="Do not stop Vulkan llama-server (may OOM on 12GB with 7B chat loaded)",
    )
    ap.add_argument("--list-presets", action="store_true")
    args = ap.parse_args(argv)
    if args.no_vram_safe:
        args.vram_safe = False
    if args.keep_vulkan:
        args.pause_vulkan = False

    if args.list_presets:
        presets_path = Path(__file__).resolve().parents[1] / "config" / "train_presets.json"
        data = json.loads(presets_path.read_text(encoding="utf-8"))
        print(json.dumps(data.get("presets") or {}, indent=2))
        print("\nInference:", json.dumps(data.get("inference") or {}, indent=2))
        return 0

    if args.preset:
        p = _load_preset(args.preset.strip())
        # Preset fills gaps; explicit CLI flags in argv always win.
        argv_l = " ".join(argv or sys.argv[1:]).lower()
        args.model = p.get("hf_model") or args.model
        if "--adapter-subdir" not in argv_l:
            args.adapter_subdir = p.get("adapter_subdir") or args.adapter_subdir
        if "--max-steps" not in argv_l and not os.environ.get("TRAIN_MAX_STEPS"):
            args.max_steps = int(p.get("max_steps_default") or args.max_steps)
        if "--max-length" not in argv_l and not os.environ.get("TRAIN_MAX_LENGTH"):
            args.max_length = int(p.get("max_length") or args.max_length)
        if "--lora-r" not in argv_l and not os.environ.get("TRAIN_LORA_R"):
            args.lora_r = int(p.get("lora_r") or args.lora_r)
        if (not args.device) and p.get("recommend_device"):
            args.device = str(p["recommend_device"])
        print(f"[train] preset={args.preset} chat_gguf={p.get('chat_gguf')}", flush=True)
        print(f"[train] notes: {p.get('notes')}", flush=True)

    dataset_path = Path(args.dataset)
    if not dataset_path.is_file():
        print(f"[train] missing dataset: {dataset_path}", file=sys.stderr)
        print("[train] run: python scripts/wire_training.py", file=sys.stderr)
        return 1

    device, backend = pick_device(args.device)
    print(f"[train] backend={backend} base={args.model}", flush=True)
    print(
        "[train] note: Vulkan llama-server = inference/chat; this script = LoRA weight training",
        flush=True,
    )

    # 12GB AMD: Vulkan 7B chat + DirectML 1.5B train will OOM — pause chat GPU server
    vulkan_up = _port_up(8080)
    if backend == "directml" and vulkan_up and args.pause_vulkan:
        print(
            "[train] Vulkan :8080 is UP (likely 7B GGUF on the 6700 XT). "
            "Pausing llama-server to free VRAM for DirectML train…",
            flush=True,
        )
        stopped = _pause_vulkan_stack()
        print(f"[train] paused: {stopped or ['(no llama-server process found)']}", flush=True)
        print(
            "[train] after training, restart chat with: "
            "powershell -File scripts\\run_local_chat.ps1",
            flush=True,
        )
    elif backend == "directml" and vulkan_up and not args.pause_vulkan:
        print(
            "[train] WARNING: Vulkan :8080 still up — expect VRAM OOM on 12GB. "
            "Re-run without --keep-vulkan, or stop llama-server first.",
            flush=True,
        )

    # Universal VRAM-safe plan (Qwen/LLaMA/Mistral/Phi/Gemma/Yi/…)
    from core.training.directml_vram_safe import (
        apply_directml_vram_safe,
        forward_with_oom_backoff,
        suggest_vram_plan,
    )

    plan = suggest_vram_plan(backend, args.model)
    print(f"[train] vram plan: {plan}", flush=True)
    if args.vram_safe:
        args.max_length = min(int(args.max_length), int(plan.max_length))
        args.lora_r = min(int(args.lora_r), int(plan.lora_r))
        args.batch_size = min(int(args.batch_size), int(plan.batch_size))
        print(
            f"[train] vram-safe applied: max_length={args.max_length} "
            f"lora_r={args.lora_r} batch={args.batch_size}",
            flush=True,
        )

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = plan.dtype
    print(f"[train] dtype={dtype} ({plan.notes})", flush=True)

    print(f"[train] loading model (low_cpu_mem_usage=True) …", flush=True)
    # transformers 4.44 uses torch_dtype; newer builds accept dtype=
    load_kw = {
        "trust_remote_code": True,
        "low_cpu_mem_usage": True,
        "torch_dtype": dtype,
    }
    if backend == "directml":
        load_kw["attn_implementation"] = "eager"
    try:
        model = AutoModelForCausalLM.from_pretrained(args.model, **load_kw)
    except TypeError:
        load_kw.pop("torch_dtype", None)
        load_kw.pop("attn_implementation", None)
        load_kw["dtype"] = dtype
        try:
            model = AutoModelForCausalLM.from_pretrained(args.model, **load_kw)
        except TypeError:
            load_kw.pop("dtype", None)
            model = AutoModelForCausalLM.from_pretrained(args.model, **load_kw)

    lora = LoraConfig(
        r=args.lora_r,
        lora_alpha=max(8, args.lora_r * 2),
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    )
    model = get_peft_model(model, lora)
    model.to(device)
    apply_directml_vram_safe(model, backend=backend, force_fp32=(backend != "cuda"))
    model.print_trainable_parameters()

    ds = JsonlTextDataset(dataset_path, tokenizer, args.max_length)
    loader = DataLoader(ds, batch_size=args.batch_size, shuffle=True)

    # AdamW is fine on CUDA/CPU; DirectML historically broke on some Adam ops → SGD
    if backend == "directml":
        from torch.optim import SGD

        opt = SGD(model.parameters(), lr=args.lr)
        print("[train] optimizer=SGD (DirectML-safe)", flush=True)
    else:
        from torch.optim import AdamW

        opt = AdamW(model.parameters(), lr=args.lr)
        print("[train] optimizer=AdamW", flush=True)

    model.train()
    step = 0
    logged_shape = False
    for batch in cycle(loader):
        if step >= args.max_steps:
            break
        out = forward_with_oom_backoff(
            model,
            batch,
            max_length=args.max_length,
            backend=backend,
            device=device,
            min_length=32,
        )
        if not logged_shape and "attention_mask" in batch:
            print(
                f"[train] first-batch shapes input_ids≈(*,{args.max_length}) "
                f"model_dtype={next(model.parameters()).dtype}",
                flush=True,
            )
            logged_shape = True
        loss = out.loss
        try:
            loss_val = float(loss.item())
        except Exception:
            loss_val = float("nan")
        if loss_val != loss_val or loss_val in (float("inf"), float("-inf")):
            print(f"[train] non-finite loss at step {step}; stopping", flush=True)
            break
        loss.backward()
        opt.step()
        opt.zero_grad(set_to_none=True)
        step += 1
        if step == 1 or step % 5 == 0 or step == args.max_steps:
            print(f"[train] step {step}/{args.max_steps} loss={loss_val:.4f}", flush=True)
        if backend == "directml" and step % 5 == 0:
            try:
                import gc

                gc.collect()
            except Exception:
                pass

    adapter_dir = Path(args.output_dir) / args.adapter_subdir
    adapter_dir.mkdir(parents=True, exist_ok=True)
    # Save from CPU to avoid backend tensor issues
    try:
        model.to("cpu")
    except Exception:
        pass
    model.save_pretrained(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))
    meta = {
        "base_model": args.model,
        "dataset": str(dataset_path),
        "max_steps": args.max_steps,
        "lora_r": args.lora_r,
        "backend": backend,
        "device": str(device),
        "inference_note": "Use Vulkan llama-server for chat; merge/register adapter separately",
    }
    (adapter_dir / "realai_train_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[train] saved adapter → {adapter_dir}", flush=True)
    print(
        "[train] next: keep using Vulkan chat (GGUF); adapter is PEFT under checkpoints_lora/",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
