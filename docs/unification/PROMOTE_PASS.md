# Promotion pass (no ghosted code)

## Promoted into living tree
1. **core/training/** — DirectML/Qwen LoRA trainers, build_datasets, finetune, eval
2. **modules/training/datasets/** — finetune jsonl + agent manifests
3. **core/memory/long_term_engine.py** + **bridge.py** — long-term memory engine
4. **core/orchestration/** — v3_orchestrator + gold pipeline/agent/tools/memory
5. **core/agents/** — self_heal, agent_runtime
6. **modules/agents_skills/** — full agents pack from recovery
7. **modules/orchestrators/** — orchestrator variants
8. **adapters/** — training.py, memory.py, agents.py + living_stack()

## Still available only under recovered/ (archived, registered)
All batch1/batch2 snapshots remain full tip trees for zero-loss.

## How core discovers them
`registry/modules.yaml` + `adapters.resolve_path(id)` + `adapters.living_stack()`.
