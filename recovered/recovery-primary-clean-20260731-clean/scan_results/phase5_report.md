# Phase 5 — Authority + Agents/Memory + Self-Heal Productization

## Goal delivered (first slice: 5D + 5B light + verify expand)

Make RealAI v3 **one-tree bootable** and able to use **agents, memory inject, tools, and self-heal** on the live Vulkan path.

## Architecture

```
C:\realai\start_v3_stack.bat
        │
        ├─ Vulkan :8080  (AMD RX 6700 XT, Qwen)
        ├─ Orchestrator :8001
        │     chat (+ agent_id, memory inject)
        │     /v1/agents
        │     /v1/tools/execute
        │     /v1/training/*  /v1/self-improve/*  /v1/self-heal/*
        └─ UI :3000  from C:\realai\apps\frontend  (also synced to Users tree)
```

## New / updated artifacts

| Path | Role |
|------|------|
| `docs/AUTHORITY.md` | Single authority map |
| `.env.v3.example` | Ports + flags |
| `start_v3_stack.bat` | One-command: Vulkan → orch → UI |
| `realai/v3_orchestrator.py` | Agents, memory inject, tools, self-heal |
| `realai/self_heal.py` | Cycle + markdown report |
| `scanners/verify_v3_matrix.py` | Expanded matrix |
| UI Settings panel | Training + agents + self-heal controls |

## Verify matrix

**22/22 PASS** (includes agents list, tools, chat with agent+memory)

## How chat gains abilities

```json
POST /v1/chat/completions
{
  "agent_id": "agent-tools-documentation-pilot",
  "memory": "on",
  "messages": [{"role": "user", "content": "..."}]
}
```

Response `realai_meta` includes `agent` + `memory_injected`.

## Self-heal (multi-repo fix itself)

| Call | Effect |
|------|--------|
| `POST /v1/self-heal/cycle` `{"apply":false}` | Assemble + dry promote + evaluate + verify |
| `POST /v1/self-heal/cycle` `{"apply":true}` | Same + curated promote apply |
| UI Settings → Self-Heal panel | Buttons for dry-run / apply |

Safety: no node_modules, no bulk 10k merge, memory only in `recovered/`.

## Boot

```bat
C:\realai\start_v3_stack.bat
```

Open **http://127.0.0.1:3000**  
Settings → **RealAI Self-Heal & Training**

## Deferred (later Phase 5 slices)

- 5A scheduled auto dry-run daemon  
- 5C full LoRA→GGUF train job  
- 5E streaming SSE proxy  
- Full MCP write tools  
