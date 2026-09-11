# RealAI anywhere — full portable toolkit

Yes: chat, code, heal, stack, models, doctor, and more from **any** project folder.

## Install once

```powershell
powershell -ExecutionPolicy Bypass -File C:\RealAI-clean\scripts\install_global.ps1
```

Then open a **new** terminal (PATH + `REALAI_HOME`).

## Model

| Variable | Meaning | Default |
|----------|---------|---------|
| `REALAI_HOME` | Install (models, scripts, package) | `C:\RealAI-clean` |
| `REALAI_WORKSPACE` | Project you are editing | **cwd** |

Override workspace: `realai -C D:\OtherApp chat "…"`

## Global commands (all on PATH)

### Everyday (any project)

| Command | What it does |
|---------|----------------|
| `realai` | Interactive craft chat in **cwd** |
| `realai-chat` | Same (`realai chat …`) |
| `realai-code` | Coding session (lists project, task-focused) |
| `realai-heal` | Project diagnostics; in RealAI-clean → curated promote |
| `realai-selfheal` | Full pipeline (product stack+promote, or project heal) |
| `realai-here` | *(via `realai here`)* show home + workspace |

### Stack / models (shared GPU from HOME)

| Command | What it does |
|---------|----------------|
| `realai-stack` | Vulkan `:8080` + orchestrator `:8001` + UI `:3000` |
| `realai-server` | Vulkan llama-server only |
| `realai-orch` | Orchestrator only (needs Vulkan up) |
| `realai-health` | Probe local endpoints |
| `realai-models` | List RealAI ids + GGUFs |
| `realai-setup` | Verify llama + models on disk |
| `realai-local` | Lightweight llama-cli API on `:8000` |
| `realai-gui` | Desktop GUI |

### Product / advanced

| Command | What it does |
|---------|----------------|
| `realai-doctor` | Install self-check |
| `realai-improve` | Ability catalog self-improve (HOME) |
| `realai-promote` | Curated promote allowlist (product tree) |
| `realai-tools` | Print this toolkit map |

### Also via `realai <cmd>`

`client` · `catalog` · `organs` · `rackup` · `serve` · `pwd` · `gpu` (=server)

## Daily flow

```bat
REM once per machine session (GPU):
realai-stack

REM in any project:
cd C:\MyApp
realai
realai-code "add error handling to main"
realai-heal
realai-health
```

### In chat

| Slash | Action |
|-------|--------|
| `/pwd` | home + workspace |
| `/list` `/read` `/grep` `/write path\|\|\|content` | edit **this** project |
| `/heal` `/git` `/gpu` | heal / git / ensure model server |

## What is *not* dumped into other projects

- Curated promote / cold-archive of `recovered/` stay product-side.
- Audit logs live under `REALAI_HOME\logs\state\` (not your app folder).
- Models always load from `REALAI_HOME\models\`.

## Without PATH

```bat
set REALAI_HOME=C:\RealAI-clean
set PYTHONPATH=C:\RealAI-clean
cd C:\MyApp
python -m realai tools
C:\RealAI-clean\bin\realai-chat.cmd
```

## Full abilities (self-contained)

See **[ABILITIES.md](ABILITIES.md)**. Multi-agent, 68 agents, rackup, organs, tool
registry, workspace tools, self-heal/extend/repair all live **inside** RealAI-clean —
no runtime bridge to another repo.
