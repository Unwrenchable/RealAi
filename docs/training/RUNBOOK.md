# RealAI SFT runbook (Travis's PC)

The fixed recipe is `realai/training/train_sft.py`: Qwen2.5-1.5B-Instruct (Apache-2.0), Qwen chat template,
loss on assistant tokens only, max_len 1024 (drops to 768, then 512, if DirectML runs out of memory),
LoRA r16/α32/dropout 0.05 on attention + MLP, AdamW lr 1e-4 with cosine schedule and 3% warmup,
3 epochs, grad-accum 16, eval loss every epoch, best adapter kept. Everything stays under `REALAI_HOME`.
Nothing touches `C:\RealAI-clean`, the `:8080` Vulkan server, or `realai_models.json`.

## 0. One-time: training venv (separate from your global Python)

Your global Python has torch 2.4.1 (DirectML) but a newer transformers that no longer imports with it,
so use a pinned venv:

```powershell
py -3.12 -m venv C:\venvs\realai-train
C:\venvs\realai-train\Scripts\python -m pip install -U pip
C:\venvs\realai-train\Scripts\python -m pip install -r requirements\train-directml.txt
C:\venvs\realai-train\Scripts\python -c "import torch_directml as d; print([d.device_name(i) for i in range(d.device_count())])"
# expect: ['AMD Radeon RX 6700 XT', 'AMD Radeon(TM) Graphics']  (the trainer picks the 6700 XT by name)
```

## 1. Session setup (every new PowerShell)

```powershell
Get-ChildItem Env:REALAI_* | ForEach-Object { Remove-Item "Env:$($_.Name)" }
cd C:\temp\realai-dsb-sources
git pull --ff-only
$env:REALAI_HOME = (Get-Location).Path
$env:REALAI_LLAMA_CPP_ROOT = 'C:\tools\llama.cpp'   # convert_hf_to_gguf.py lives here
$PY = 'C:\venvs\realai-train\Scripts\python.exe'
$BASE = 'C:\models\hf\Qwen2.5-1.5B-Instruct'   # local HF weights (3.09 GB safetensors), no download
```
Pass `--base-model $BASE` to **every** `train_sft` command (train/eval/export/register) so they all use the same base.

Verified 2026-10-10: Python 3.12.3, torch 2.4.1 + torch-directml 0.2.5.dev240914, transformers 4.46.3, peft 0.13.2,
accelerate 1.1.1, numpy 2.5.3. DML devices: `AMD Radeon RX 6700 XT` (index 0, selected by `--dml-adapter "RX 6700"`),
`AMD Radeon(TM) Graphics` (iGPU, never picked). Export tools: `C:\tools\llama.cpp\convert_hf_to_gguf.py`
(@9adc7f4, has its own gguf-py) and `C:\llama-vulkan\llama-quantize.exe` (Q5_K_M supported).

## 2. Build the dataset

```powershell
New-Item -ItemType Directory -Force datasets\_sources | Out-Null
git fetch origin feature/ui-desktop-promote
cmd /c "git show origin/feature/ui-desktop-promote:dataset.jsonl > datasets\_sources\persona_dump.jsonl"   # byte-exact, no BOM
& $PY -m pip install -r requirements\dataset-builder.txt                         # python-chess, zstandard (once)
# Stockfish (once): official build unzipped under C:\tools\stockfish (found automatically; or set REALAI_STOCKFISH)
& $PY -m realai.training.dataset_builder.fetch_lichess_puzzles --rows 1500 --scan 30000   # ~2 MB streamed, CC0
& $PY -m realai.training.dataset_builder --config config\dataset_builder.pc.json --dry-run   # counts only
& $PY -m realai.training.dataset_builder --config config\dataset_builder.pc.json
$DS = (Get-ChildItem datasets -Directory -Filter 'realai-sft-*' | Sort-Object LastWriteTime | Select-Object -Last 1).FullName
Get-Content "$DS\manifest.json" | Select-String '"kept"|"train"|"eval"'
```

`ATTRIBUTION.md` sits next to the dataset. It holds the MIT notice for agency-agents. Keep it with any copy of the data or the model.

Optional: `& $PY -m realai.core.device_profile` prints this machine's hardware and the recommended model/quant/ctx/device.

## 3. Dry run (checks data and prints the plan; loads no model)

```powershell
& $PY -m pytest tests\training -q
& $PY -m realai.training.train_sft train --dataset $DS --dry-run --base-model $BASE
```
Check `"ok": true` and that `issues` is empty (sha256 matches the manifest, no eval/train overlap). The plan also shows optimizer steps (about 100 per epoch for 1.6k rows).

## 4. Train

Stop the `:8080` llama-server first (Ctrl+C in its window). It holds about 6 GB of the 6700 XT's 12 GB.
```powershell
& $PY -m realai.training.train_sft train --dataset $DS --base-model $BASE --device directml --dml-adapter "RX 6700"
```
* Logs go to the console and to `runs\sft-<dataset>\train.log`. Step 1 prints s/step and an ETA.
* Smoke first (about 3 min, saves nothing):
  `& $PY -m realai.training.train_sft train --dataset $DS --base-model $BASE --device directml --dml-adapter "RX 6700" --max-steps 10 --eval-smoke --eval-rows 20 --out runs\smoke-10`
* Measured 2026-10-10 on the RX 6700 XT (fp32 base, LoRA, grad checkpointing, batch 1 × accum 16):
  base eval loss 3.79 → 3.58 after 10 steps, train loss about 3.0, **11.3 s/step, about 60 min for the full 318 steps**
  (+ about 1 min eval per epoch). VRAM about 11.3 GB of 12 (whole adapter), so **`:8080` must be stopped**.
  Rows that OOM at 1024 are retried at 768, then 512 (one 849-token row did that in the smoke), then skipped.
* Data is short (mean 119 tokens/row, p95 253, max 852).
* Output: `runs\sft-<dataset>\adapter_best` (lowest eval loss), `adapter_last`, `train_result.json`.

## 5. Eval against the base model on the held-out set

```powershell
& $PY -m realai.training.train_sft eval --dataset $DS --base-model $BASE --device directml
```
Writes `eval_report.json`. **Pass bar:** tuned eval loss is at least **10% lower** than base and **≤ 1.5**
(exit code 0 = pass, 1 = fail). After it passes, also do a manual spot check (step 7) with 10 eval prompts. Include
Pyramid points, a shot-map route, and the hive identity. Answers must match the code/catalogue values.

## 6. Export: merge → GGUF f16 → Q5_K_M (reuses `realai/scripts/train_to_chat_gguf.py` helpers)

```powershell
& $PY -m realai.training.train_sft export --dataset $DS --base-model $BASE --model-id realai-sft-1.5b --quant Q5_K_M
```
The merge runs on CPU (about 5 min, about 7 GB RAM). Output: `runs\sft-<dataset>\gguf\realai-sft-1.5b-Q5_K_M.gguf` (about 1.1 GB).

## 7. Register (honest candidate, never default) and serve on :8081

```powershell
& $PY -m realai.training.train_sft register --dataset $DS --base-model $BASE --model-id realai-sft-1.5b
# -> $env:REALAI_HOME\models\trained_catalog.json: base_model, trained:true, dataset_manifest_sha256,
#    eval numbers, status candidate-passed / candidate-not-passed, default:false
$G = "$((Get-ChildItem runs -Directory | Sort-Object LastWriteTime | Select-Object -Last 1).FullName)\gguf\realai-sft-1.5b-Q5_K_M.gguf"
Start-Process C:\llama-vulkan\llama-server.exe -ArgumentList "-m `"$G`" --host 127.0.0.1 --port 8081 -c 4096 -ngl 99 --jinja"
$body = @{ messages = @(@{ role='user'; content='How many points to win RackUp Pyramid at beginner level?' }); max_tokens = 120 } | ConvertTo-Json -Depth 4
Invoke-RestMethod -Uri http://127.0.0.1:8081/v1/chat/completions -Method Post -ContentType 'application/json' -Body $body | % { $_.choices[0].message.content }
# expect: 25 on a 7-foot table (10-ball rack), 40 on a 9-foot table (15-ball rack).
```
`:8080` stays as it is. You can restart it after training; a 1.5B Q5 model on `:8081` fits alongside it.
Only promote the model (edit `realai_models.json` / swap the chat GGUF) after the pass bar and the spot check both pass.
