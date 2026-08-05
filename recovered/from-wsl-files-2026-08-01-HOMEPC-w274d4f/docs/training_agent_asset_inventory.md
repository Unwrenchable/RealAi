# Agent, Memory, Skill Assets for Training

This inventory gathers the local RealAI assets that look intended for agent
implementation, memory, skills, tools, and future training.

Note: the GitHub connector is authenticated as `Unwrenchable`, but currently has
no installed repository access in this Codex session. This inventory is based on
the checked-out workspace and local historical backup folders.

## High-Value Training Sources

| Area | Files | Why it matters | Training readiness |
| --- | --- | --- | --- |
| Self-builder traces | `realai/datasets/processed/self_builder_sessions.jsonl`, `realai/training/extract_from_agent_tools.py` | Converts agent tool traces into instruction/chat samples. | Already wired into `python -m realai.training.pipeline --stage ingest` and `--stage datasets`. |
| Agent protocol | `realai/agent_protocol.py`, `realai/self_builder.py`, `realai/repo_tools.py` | Strict tool-call protocol, parser retries, repo tool execution, session logging. | Good SFT source after filtering failed/fallback traces. |
| Orchestration package | `realai-orchestration/agent.py`, `orchestrator.py`, `pipeline.py`, `memory.py`, `tools.py`, `README.md` | Clean multi-agent primitives: BaseAgent, SharedMemory, ToolRegistry, pipelines, routing. | Strong implementation target and documentation-derived training data. |
| Core agent stack | `core/agents/planner.py`, `worker.py`, `critic.py`, `executor.py`, `synthesizer.py`, `safety.py` | Planner/worker/critic/synthesizer agent roles with tool safety. | Good architecture source; needs integration tests before training as behavior examples. |
| Chat pipeline | `core/inference/chat_pipeline.py` | Memory retrieval, tool loop, summarization, persistent message storage. | Good implementation target; verify current API compatibility before using as canonical behavior. |
| Memory systems | `core/memory/sqlite_store.py`, `core/memory/summarizer.py`, `realai/server/memory_store.py`, `aura/memory.py` | Multiple memory designs: SQLite search/summaries, server memory API, file-based long-term memory. | Useful for training examples and consolidation. |
| Skill systems | `aura/skills/*`, `core/tools/*`, `realai/server/tools_runtime.py` | Skill registries, tool permissions, file/code/web/web3 tools. | Good source for tool-use training and implementation cleanup. |
| Agent specs | `agents/*.md`, `agents/*.json`, `agents/templates/*`, `agents/runtime/*` | Intended agent personas, repo guidance, memory notes, TS runtime sketches. | Good prompt/spec data; not all runnable. |
| Legacy agent app | `realai_agent/*` | Older hierarchical/supervisor/Rise agent system and training pipeline ideas. | Mine for concepts; validate before direct integration. |

## Current Local Model Path

- Fast GUI/default loop model: `llama-local-1b`
- Slow opt-in model: `qwen-coder-7b`
- LoRA adapter: `checkpoints_lora/qwen2.5-1.5b-lora`

The LoRA adapter is not currently a drop-in replacement for the GUI model list,
because the GUI/server registry runs GGUF backends while the adapter requires a
Transformers + PEFT + DirectML runtime. Use `chat_qwen_lora_directml.py` for the
adapter until a PEFT backend or GGUF export path is added.

## Immediate Training Pipeline

Use this sequence to gather current self-builder behavior:

```powershell
cd C:\Users\tsmit\realai
.\.venv\Scripts\Activate.ps1
python -m realai.closed_loop --iterations 2
python -m realai.training.pipeline --stage ingest
python -m realai.training.pipeline --stage datasets
```

Then train the DirectML LoRA adapter:

```powershell
python train_qwen_lora_directml.py
python chat_qwen_lora_directml.py
```

## Integration Work Still Needed

1. Add filtering for failed self-builder traces before they enter
   `instructions.jsonl`.
2. Consolidate memory APIs around one canonical store or adapter layer.
3. Decide whether LoRA should be served through a PEFT backend or merged/exported
   to GGUF for the existing GUI path.
4. Convert `realai-orchestration` examples into tests and training samples.
5. Promote selected `aura/skills` into `core/tools` or mark them legacy.
6. Add a repo scanner for future GitHub-connected imports once the GitHub app has
   installed repository access.

## Historical Backup Repos Found Locally

Nested `.git` folders were found under:

- `realai_historical_backups/realai_versions_20260612/real-fin/realai`
- `realai_historical_backups/realai_versions_20260612/RealAIProject`

These should be mined separately for older agent, memory, and model registry
variants before deletion or cleanup.
