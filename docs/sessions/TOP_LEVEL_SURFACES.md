# Top-level vs buried RealAI surfaces

**Catalog honesty (live):** 62 abilities · 116 tools · 245 agents (hive cores + agency) — already on Hive `:8001`.

## Already top-level (use these)

| Surface | How to reach |
|---------|----------------|
| Console chat | `/console` or VS Code RealAI Console — plain English |
| Capability card | say `hey` / `what can you do?` |
| Tools catalog | `/tools` |
| Hive cores | `/hive` · Agents UI **Hive** filter |
| Multi-agent | `/multi <task>` |
| Self-heal | `/heal` |
| Nest orchestrators | `/nests` |
| Omnibrain / world | `/omnibrain` · `/world` |
| Overseer | `/overseer` |
| Code engineer | `/engineer` · `/code-engineer` |
| Hierarchy | `/hierarchical` · `/specialists` |
| Voice | SPEAK toggle · `/speak …` · Kokoro local |
| Shell | `$ cmd` (real processes only) |

## Buried under `realai/` (do **not** promote wholesale)

Hundreds of duplicate / archive modules (`realai/agents/*`, `plugin_system`, `exportable/variants`, nested orchestrator copies). These are **implementation debris**, not missing product features. Promoting them would re-break imports.

**Keep buried:** anything under `plugin_system/`, `_archive`, `exportable/variants`, duplicate `realai_*` twin modules already wired via `abilities/*.py` + `v3_runtime_bridge`.

## P0 promotions done this pass

- Natural-talk capability card (`realai/bot/talk_easy.py`)
- Easy aliases: nests, hierarchical, engineer, hominis, governance, quarantine, cli, deep-promote, brain
- Console empty-state chips for plain-English starters
- Hive cores on Agents UI graph (prior turn)

## P1 later (optional)

| Idea | Why |
|------|-----|
| Fusion “Start here” strip | Same capability card + chips |
| Collapse duplicate `realai/agents` twins | Reduce import shadowing risk |
| Wire `desktop_lambda_*` into Ops “Creative” tab | Already LIVE abilities; UX only |
