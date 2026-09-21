# Hive agents index (2026-09-21)

One map of agent-like files in `C:\RealAI-clean`. **Do not** copy every agent into `realai/`. Live hive seats are JSON under `.github/agents/` plus Python under `agents/hive/`. Runtime: `realai/orchestration/hive_router.py`, `POST /v1/agents`, `POST /v1/multi-agent/run`.

## Live `/v1/agents` (probe)

Hive required (from `/v1/hive`): `overseer`, `coder`, `architect`, `analyst`, `memory`, `governor`, `router`.

`/v1/agents` returns a large catalog (pipeline + hive + third-party style ids). Hive role ids present in that list include at least:

`analyst`, `architect`, `coder`, `executor`, `governor`, `guardian`, `hive-orchestrator`, `memory`, `overseer`, `planner`, `router`, `self-heal`

(Plus many non-hive catalog entries such as `researcher`, `creative`, `critic`, game/marketing specialists, etc.)

## Counts

| source | count | class |
|--------|------:|-------|
| `.github/agents/*.json` | 12 | **HIVE** |
| `.github/agents/*.agent.md` | 8 | **COPILOT** |
| `agents/hive/*.py` (excl. `__init__`) | 7 | **HIVE** (runtime seats) |
| `agents/*.agent.json` | 9 | **DUMP** (legacy sidecars) |
| `agents/*.agentx` | 13 | **DUMP** (legacy agentx) |
| `agent_tools/` top-level files+dirs | 42 | **TOOL** (impl surface; not hive roles) |
| `.agents/` | 0 (missing) | — |
| `apps/vscode` `languageModelChatProviders` | 1 vendor `realai` | **TOOL** (IDE chat provider) |

## Table

| id | path | class | on `/v1/agents`? | notes |
|----|------|-------|------------------|-------|
| overseer | `.github/agents/overseer.json` | HIVE | Y | `hive: true`; Python seat `agents/hive/overseer.py` |
| coder | `.github/agents/coder.json` | HIVE | Y | + `agents/hive/coder.py` |
| architect | `.github/agents/architect.json` | HIVE | Y | + `agents/hive/architect.py` |
| analyst | `.github/agents/analyst.json` | HIVE | Y | + `agents/hive/analyst.py` |
| memory | `.github/agents/memory.json` | HIVE | Y | + `agents/hive/memory.py` |
| governor | `.github/agents/governor.json` | HIVE | Y | + `agents/hive/governor.py` |
| router | `.github/agents/router.json` | HIVE | Y | + `agents/hive/router.py` |
| executor | `.github/agents/executor.json` | HIVE | Y | JSON role; no `agents/hive/executor.py` |
| planner | `.github/agents/planner.json` | HIVE | Y | JSON only |
| guardian | `.github/agents/guardian.json` | HIVE | Y | JSON only |
| self-heal | `.github/agents/self-heal.json` | HIVE | Y | JSON only |
| hive-orchestrator | `.github/agents/hive-orchestrator.json` | HIVE | Y | JSON only |
| *(hive package)* | `agents/hive/__init__.py` | HIVE | — | package init |
| browser-test-engineer | `.github/agents/browser-test-engineer.agent.md` | COPILOT | Y (catalog id) | Copilot Chat agent md — leave in `.github` |
| cybersecurity-expert | `.github/agents/cybersecurity-expert.agent.md` | COPILOT | Y | leave |
| game-creative-director | `.github/agents/game-creative-director.agent.md` | COPILOT | Y | leave |
| game-designer | `.github/agents/game-designer.agent.md` | COPILOT | Y | leave |
| game-technical-director | `.github/agents/game-technical-director.agent.md` | COPILOT | Y | leave |
| gameplay-programmer | `.github/agents/gameplay-programmer.agent.md` | COPILOT | Y | leave |
| my-agent | `.github/agents/my-agent.agent.md` | COPILOT | N/partial | sample |
| tokenized-agents | `.github/agents/tokenized-agents.agent.md` | COPILOT | N/partial | sample |
| coder / fallback / master / memory / npc / overseer / router / sandbox / worker | `agents/*.agent.json` | DUMP | some ids overlap catalog | Legacy JSON next to agentx — do not promote into `realai/` |
| architect, code_engineer, code_reviewer, debugger, devops, documentation, master, memory_summarizer, npc_intel, overmind, router, security, task_planner | `agents/*.agentx` | DUMP | — | Legacy agentx packs |
| *(tool modules)* | `agent_tools/*.py` + `agents_impl/`, `engine/`, `providers/`, `tooling/` | TOOL | — | Tooling/runtime helpers — not hive role defs |
| realai (vendor) | `apps/vscode` `contributes.languageModelChatProviders` | TOOL | — | IDE “RealAI Hive” chat provider |

## Python seats vs JSON

| `agents/hive/*.py` | matching `.github/agents/*.json` |
|--------------------|----------------------------------|
| overseer, coder, architect, analyst, memory, governor, router | all present |

**New JSON this pass: none** (every Python hive seat already has a HIVE json; max-5 rule unused).

## Authority

| layer | path |
|-------|------|
| Role cards (hive) | `.github/agents/*.json` |
| Python seats | `agents/hive/*.py` |
| Router / nests | `realai/orchestration/hive_router.py` |
| HTTP | `GET /v1/agents`, `GET /v1/hive`, `POST /v1/multi-agent/run` |
| Copilot personas | `.github/agents/*.agent.md` (do not move into `realai/`) |
| HOMEPC / nested agent dumps | stay DUMP — do not touch |

## Refused

- No mass copy of agents into `realai/`
- No recovery merges
- No Copilot `.md` moves
- No `agent_runtime` HOMEPC dump edits
