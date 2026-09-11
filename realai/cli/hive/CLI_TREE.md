# RealAI Hive CLI — Command Tree

Identity: **orchestrator-centric · agent-aware · GPU-honest · workspace-grounded**  
Not Craft. Not a chat REPL by default.

```
realai                          # startup banner + surface status
├── status [--json]
├── doctor [--json]
├── version
│
├── stack
│   ├── up                      # vulkan resume + orch start
│   ├── down                    # pause vulkan (VRAM)
│   └── status
├── gpu
│   ├── status                  # C:\llama-vulkan + checkpoints_lora
│   ├── start | resume [--gguf]
│   └── stop
├── orch
│   ├── status
│   └── start
├── vulkan                      # alias → gpu status
│
├── models [--limit N]
├── providers
│
├── route <task>                # decide agent (no side effects)
│   ├── -x / --execute          # run as that agent
│   └── --multi                 # pipeline instead
├── routes                      # keyword→archetype map
├── run <task>                  # default: multi-agent pipeline
│   ├── --no-multi --agent ID
│   └── --max-tokens N
├── agents [--hive] [-q TEXT]
│   ├── list
│   ├── info <id>
│   └── run <id> <task>
├── multi <task> [--mode pipeline|parallel]
├── task
│   ├── list | get <id> | create <task>
│
├── abilities [--live]
│   └── list
├── ability run <name> [--input …]
├── tools
│   └── list
├── tool exec <name> [--arg k=v]
│
├── heal
│   ├── status | cycle | assemble | promote [--apply]
├── world
│   ├── show | query <q>
├── quarantine
│   ├── status | scan | list [--promote-only] | find <q>
│
├── chat <prompt> [--agent] [--multi]
├── ask <prompt>
└── craft […]                   # compat escape hatch only
```

## Folder structure

```
realai/cli/hive/
  app.py                 # entry (console_scripts → here)
  banner.py              # startup identity + status collect
  client.py              # HiveClient HTTP
  context.py             # Click ctx
  format.py              # tables / errors / json
  agent_router.py        # task → archetype routing
  ability_runner.py      # ability catalog + execute
  world_inspector.py     # world-model read paths
  gpu_inspector.py       # vulkan_runtime wrapper
  commands/
    status.py stack.py models.py
    route.py run.py agents.py multi.py tasks.py
    abilities.py tools.py heal.py world.py
    quarantine.py chat.py craft_cmd.py
```

## Entry points

| Invoke | Target |
|--------|--------|
| `realai` / `realai-cli` | `realai.cli.hive.app:main` |
| `python -m realai` | same |
| `realai-craft` | Craft (secondary) |

## Core modules (pro surfaces)

| Module | Role |
|--------|------|
| `agent_router` | Keyword + roster routing; `run_routed` |
| `ability_runner` | Honesty catalog + `ability.*` execute |
| `world_inspector` | WORLD_STATE / JSON artifact inspect |
| `gpu_inspector` | paths/health/resume/stop via `scripts/vulkan_runtime.py` |
