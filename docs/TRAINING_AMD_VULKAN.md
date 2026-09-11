# Training on AMD / Vulkan machines (and for all users)

## Two different GPU jobs (both wired on your PC)

| Job | Engine | Your AMD box |
| --- | --- | --- |
| **Chat / inference** | `C:\llama-vulkan\llama-server.exe` **Vulkan** GGUF → orch `:8001` | ✅ Keep running (`run_local_chat.ps1`) |
| **LoRA fine-tune** | PyTorch + PEFT + **DirectML** (RX 6700 XT) | ✅ `train_lora_local.py --device directml` |

**Vulkan cannot train Hugging Face LoRA adapters.** Chat stays on Vulkan; training uses DirectML. Both can run at once (12GB VRAM — pause heavy chat load if 7B train OOMs).

Check both:

```powershell
python scripts/amd_stack_status.py
```

## Universal DirectML VRAM-safe patch

Drop-in module (auto-used by `train_lora_local.py`):

`core/training/directml_vram_safe.py` (also `realai.training.directml_vram_safe`)

- auto VRAM plan (`REALAI_VRAM_GB=12` on your 6700 XT)
- force **fp32** model + finite causal masks (no `-inf` / uint8 overflow)
- patch Qwen / LLaMA / Mistral / Gemma / Phi / Yi / Falcon / GPT-NeoX / StarCoder mask helpers
- disable gradient checkpointing + KV cache on DirectML
- clamp sequence length + OOM backoff
- log dtype / mask shapes once

```python
from core.training.directml_vram_safe import apply_directml_vram_safe, suggest_vram_plan
plan = suggest_vram_plan("directml", "Qwen/Qwen2.5-1.5B-Instruct")
apply_directml_vram_safe(model, backend="directml")
```

## One command: train → merge → GGUF → swap into Vulkan chat

Default = **qwen-coder-7b** (replaces your chat GGUF):

```powershell
cd C:\RealAI-clean
# first time: ensure training data wired
python scripts\dispatch_training.py

# ONE COMMAND (pauses Vulkan, trains, merges, quantizes Q5_K_M, swaps GGUF)
python scripts\train_to_chat_gguf.py
# same as:
python scripts\train_to_chat_gguf.py --preset qwen-coder-7b --device directml --max-steps 30 --restart-chat
```

Safer / faster on 12GB:

```powershell
python scripts\train_to_chat_gguf.py --preset qwen-1.5b --max-steps 50 --restart-chat
```

Merge/export only (adapter already trained):

```powershell
python scripts\train_to_chat_gguf.py --preset qwen-coder-7b --skip-train --restart-chat
```

Dry-run (print plan only):

```powershell
python scripts\train_to_chat_gguf.py --dry-run
```

## Train other models (presets) — LoRA only (no GGUF swap)

```powershell
cd C:\RealAI-clean
python scripts/wire_training.py
python scripts/train_lora_local.py --list-presets

# DirectML on RX 6700 XT
python scripts/train_lora_local.py --preset qwen-0.5b --device directml --max-steps 50
python scripts/train_lora_local.py --preset qwen-coder-1.5b --device directml --max-steps 100
python scripts/train_lora_local.py --preset qwen-coder-7b --device directml --max-steps 50
python scripts/train_lora_local.py --preset llama-3.2-1b --device directml --max-steps 100
```

Each preset maps an HF train base → adapter folder under `C:\models\checkpoints_lora\` and (when available) the matching **chat GGUF** for Vulkan.

After LoRA: chat still uses the GGUF until you merge/export the adapter. Existing chat stack does not need to restart for training.

## Portable train command (works for you and other users)

```powershell
cd C:\RealAI-clean
python scripts/wire_training.py
python scripts/train_lora_local.py --preset qwen-coder-1.5b --device directml --max-steps 50
```

Device auto-order:

1. **DirectML** (AMD Windows) — if `torch-directml` loads
2. **CUDA** (NVIDIA)
3. **CPU** — always available

Force a backend:

```powershell
$env:REALAI_TRAIN_DEVICE = "cpu"        # safest / most portable
$env:REALAI_TRAIN_DEVICE = "directml"   # AMD GPU train when DLL matches torch
$env:REALAI_TRAIN_DEVICE = "cuda"       # NVIDIA only
```

## Fix DirectML on this AMD box (RX 6700 XT)

You already have Microsoft.AI.DirectML under `C:\DirectML`. Wire it once:

```powershell
powershell -ExecutionPolicy Bypass -File C:\RealAI-clean\scripts\setup_directml_amd.ps1
```

That script:

1. **Robocopies** `C:\DirectML\bin\x64-win\DirectML.dll` →  
   - `C:\DirectML\runtime\x64` (user PATH)  
   - `vendor\directml\x64`  
   - Python `torch_directml` package folder  
2. Installs **torch==2.4.1** (required by `torch-directml 0.2.5`)  
3. Probes `torch_directml.device()` (should print `privateuseone:0`)

Then train on the 6700 XT (**pause Vulkan chat first** — same 12GB VRAM):

```powershell
# new terminal so PATH picks up C:\DirectML\runtime\x64
# Script auto-stops llama-server unless you pass --keep-vulkan
python scripts/train_lora_local.py --preset qwen-1.5b --device directml --max-steps 50

# after train, bring chat back:
powershell -ExecutionPolicy Bypass -File scripts\run_local_chat.ps1
```

If you see `not enough GPU video memory`: Vulkan 7B GGUF was still loaded. Let the script pause it (default), or manually:

```powershell
taskkill /IM llama-server.exe /F
python scripts/train_lora_local.py --preset qwen-1.5b --device directml --max-steps 50 --max-length 128 --lora-r 8
```

Avoid starting **7B / Coder-1.5B downloads** while experimenting — use `--preset qwen-1.5b` (Instruct weights you already began caching).

If DirectML ever breaks again, CPU still works:

```powershell
python scripts/train_lora_local.py --model Qwen/Qwen2.5-0.5B-Instruct --max-steps 20 --device cpu
```

Keep **Vulkan chat** unchanged either way.

## Wired RealAI training sources

Built by `scripts/wire_training.py` into:

`C:\models\checkpoints_lora\datasets\normalized_datasets\realai_lora_ready.jsonl
(also available via junction at `C:\models\checkpoints_lora\normalized_datasets\…`)`

Includes:

- `realai/plugins/dataset.jsonl` (main `text` corpus)
- `training/data/realai_finetune_dataset.jsonl`
- `training/data/ability_surface.jsonl`
- grok_export / modules training JSONL
- agent manifests mirrored under `checkpoints_lora/realai_training_data/`

**Do not** use `C:\models\normalized_datasets\train_combined.jsonl` — it is a misnamed multi-JSON config dump (~4GB), not a dataset.

## Existing adapters

`C:\models\checkpoints_lora\` already has many agent LoRA runs + `qwen2.5-1.5b-lora`.  
New RealAI runs go to `qwen2.5-1.5b-lora-realai\` by default.

`peft_merge_list.txt` is refreshed by `wire_training.py`.

## After training

1. Adapter folder under `C:\models\checkpoints_lora\<name>\`
2. Chat still uses Vulkan GGUF until you merge/export
3. Optional: `python -m realai.training.pipeline --stage export` when you have an HF merge

## Status check

```powershell
python -c "from adapters.training import training_status; import json; print(json.dumps(training_status(), indent=2)[:2000])"
```

