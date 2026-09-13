# RealAI-clean ability surface (self-contained)

Everything below lives **inside** `C:\RealAI-clean`. No runtime dependency on `C:\realai`.

## Architecture

```
realai / UI (@realai/design-system tokens + components)
    -> orchestrator :8001
         tools catalog (v3_runtime_bridge)
         agents / Hive roster (hundreds in catalog; cast varies by UI)
         multi-agent pipeline
         plugins/rackup_coach
         modules/organs
         self_heal / self_extend / self_repair
         workspace file tools
         self-build (self_builder / closed_loop)
    -> Vulkan :8080 (model)
```

## Frontend design system

| Path | Role |
|------|------|
| `packages/design-system/` | Prebuilt UI kit + `tokens.cjs` |
| `packages/ui/` | Facade re-export |
| `frontend/tailwind.config.js (and/or apps/frontend legacy)` | Merges design tokens into Tailwind |
| `frontend/lib/design.ts` | Brand colors for TS components |

```tsx
import { Button, ChatBubble } from "@realai/design-system";
// or tokens only:
import { colors } from "@realai/design-system/tokens"; // via require in CJS
```

## In-tree modules that make abilities real

| Module | Role |
|--------|------|
| `realai/v3_runtime_bridge.py` | Tools catalog, multi-agent, agent-tools roster, web research, sandbox code |
| `realai/v3_orchestrator.py` | HTTP API, tool execute, chat + multi_agent |
| `realai/agent_runtime.py` | MultiAgentPipeline + organs fusion |
| `realai/server/tools/*` | self_extend, self_repair, system_scan |
| `realai/tools.py` | TOOL_REGISTRY (builtins + ability.*) |
| `realai/ability_catalog.py` | Honesty map of LIVE / PARTIAL / STUB |
| `agents/agentx/agents.json` | 68 agent definitions |
| `plugins/rackup_coach` | Game/rating plugin |
| `modules/organs` | Synthetic organs hive |

## Use in chat

```bat
realai-stack
realai
```

Slash tools:

- `/tools` `/agents` `/multi <task>` `/exec <name> {...}`
- `/extend` `/repair` `/scan` `/heal` `/task` `/rackup`
- `/list` `/read` `/write` `/grep` (workspace)

API:

```http
GET  /v1/tools
POST /v1/tools/execute  {"name":"multi_agent_run","arguments":{"task":"..."}}
POST /v1/multi-agent/run
GET  /v1/agents
GET  /v1/capabilities
POST /v1/chat/completions  multi_agent=true
```

## Self-build / training (ported in-tree)

| Command | Module |
|---------|--------|
| `realai-build "…"` | `realai.self_builder` |
| `realai-loop` | `realai.closed_loop` |
| `realai-train --stage status` | `realai.training.pipeline` |
| `start_self_build.bat` | launcher |
| `docs/SELF_BUILD_LOCAL.md` | guide |

Repo tools: `read_file`, `list_dir`, `grep`, `search_replace`, `run_terminal_command`  
Weights: `realai.model_assets` (flat `models/*.gguf` + branded dirs)

## Coverage

Run:

```bat
realai catalog
python -c "from realai.ability_catalog import coverage_summary; print(coverage_summary()['coverage'])"
```

LIVE abilities grow as handlers exist in this repo — not by copying another tree.
