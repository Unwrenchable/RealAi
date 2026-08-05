# Machine-wide RealAI gold map (C: drive + user profile)

Scanned 2026-07-13 for misplaced models, training data, standalone builds, and alternate repos.
Skipped pure noise (Windows, node_modules, most AppData caches) where possible.

## Unique real GGUF weights (not stubs)

Same content appears in **many** folders (copies for git-safe trees vs working trees).

| Model | Size | Canonical / copies |
|-------|------|--------------------|
| **Qwen2.5-Coder-7B Q5_K_M** | ~5.19 GB | `C:\realai\models\…` · `C:\llama-vulkan\models\…` · `C:\llama\models\…` · `C:\Users\tsmit\Documents\models\…` · `~\.ollama\models\` (+ `__dup1`) |
| **Llama-3.2-1B Instruct Q4_K_M** | ~770 MB | `C:\realai\models\…` · `C:\llama-vulkan\…` · `C:\llama\models\…` · `Documents\models\…` · OneDrive Desktop copies |
| **realai-1.0-instruct** (bootstrap = Llama-class) | ~770 MB | `C:\llama-vulkan\models\realai-1.0\weights\` · `~\.ollama\models\realai-1.0-instruct-Q4_K_M.gguf` · hardlinked into `C:\realai\models\realai-1.0\weights\` |

**Not found:** a *distinct* fine-tuned GGUF larger/different from these (no unique trained Qwen export on disk).

## Training GOLD (this is the “you trained” trail)

| Path | Size | Notes |
|------|------|-------|
| `C:\Users\tsmit\Downloads\realai_finetune_dataset.jsonl` | ~36 KB | Real instruction/response finetune samples (RealAI-domain) |
| `C:\Users\tsmit\Downloads\agent_manifests_for_finetuning.json` | ~77 KB | Agent role manifests for finetune |
| `C:\llama-vulkan\start_server.bat` | tiny | Runs `train_from_agent_manifests.py` under `C:\Users\tsmit\realai` |
| `C:\realai\realai\training\finetune.py` | stub | Plan-only, not a finished trainer |

**Interpretation:** training *data* and *pipeline intent* exist; a finished custom weight export still does **not** show up as a unique GGUF.

## Alternate RealAI code trees

| Location | What’s there |
|----------|----------------|
| `C:\realai` | Main super-repo (current work) |
| `C:\Users\tsmit\realai` | Older/fuller tree: huge `.git` LFS objects, `realai-core.tar.gz` (~9 GB LFS + multi‑GB parts), installers, dist `RealAI.exe` |
| `C:\Users\tsmit\Documents\GitHub\realai` | GitHub clone (code; check for configs) |
| `C:\Unwrenchable\realai` | Org folder sibling to Atomic Fizz vault |
| `C:\tools\realai` | Tiny CLI shell (many empty plugin stubs) |
| OneDrive Desktop `realai` / `realai - Copy` | Standalone **RealAI.exe** (~208 MB), launcher build artifacts, memory json/db |

## Inference runtimes (standalone)

| Path | Role |
|------|------|
| `C:\llama-vulkan\` | Vulkan llama.cpp + models (your “standalone” stack) |
| `C:\llama\` | Another llama tree + same Qwen/Llama GGUFs |
| `C:\llama.cpp\` | Source/build tree |
| `~\.ollama\models\` | Ollama copies + Modelfile-qwen / Modelfile-realai |

## Huge archives worth knowing (not chat weights)

| Path | Size | Notes |
|------|------|-------|
| `C:\Users\tsmit\realai\realai-core.tar.gz` | multi‑GB | Core export; may hold older snapshots |
| `C:\Users\tsmit\realai\.git\lfs\objects\…` | ~9 GB object | Git LFS blob (possibly models historically) |
| `archive\Output\RealAI-Setup.exe` etc. | ~600 MB+ | Installers |

## Bottom line

1. **Weights that can run chat today:** Qwen 7B + Llama/realai-1.0 bootstrap — already under `C:\realai\models` and `C:\llama-vulkan\models`.  
2. **Misplaced training gold:** Downloads finetune **jsonl** + **agent manifests** — recover these into `C:\realai` if you want to retrain.  
3. **Misplaced product gold:** OneDrive Desktop **RealAI.exe** builds; `C:\Users\tsmit\realai` LFS/tar for older full trees.  
4. **No second mystery trained GGUF** found on C: under user + common roots; if it exists, likely external drive, cloud only, or inside multi‑GB tar/LFS not yet extracted.

## Suggested recovery (when you want)

```text
# training data into repo
copy Downloads\realai_finetune_dataset.jsonl  → C:\realai\training\data\
copy Downloads\agent_manifests_for_finetuning.json → C:\realai\training\data\

# optional: inspect old tree
# C:\Users\tsmit\realai\realai-core.tar.gz
```
