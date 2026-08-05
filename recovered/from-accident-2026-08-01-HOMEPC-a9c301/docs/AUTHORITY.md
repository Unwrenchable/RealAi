# RealAI v3 Authority Map

**Single product root:** `C:\realai`

## Authority (edit / run here)

| Tree | Role |
|------|------|
| `realai/` | Python package — orchestrator, self_heal, self_improvement, API |
| `apps/frontend` | **v3 Next.js UI** (canonical) |
| `agents/` | Agent definitions including `agents/agentx/` |
| `packages/` | SDKs (sdk-ts, sdk-py, cli) |
| `core/`, `providers/`, `plugins/`, `training/` | Supporting authority |
| `scanners/` | Discovery / promote tools (not product runtime) |
| `C:\llama-vulkan\` | **Inference only** (AMD Vulkan llama-server) — not merged as app code |

## Gold sources (read / promote uniques only)

| Tree | Role |
|------|------|
| `realai_og_mess/` | OG messy tree |
| `archive/` | Archived + accidental moves |
| `.backup/`, `*__dup*`, `Copy` | Duplicates — prefer authority hash |
| `C:\Users\tsmit\realai` | Secondary older tree (UI used to live here) |
| `recovered/` | Staging for promoted gold |

## Noise (never promote)

`node_modules`, `venv`, `.vs`, `build`, `dist`, `__pycache__`, `.next`, `phase4_tools`, multi‑GB cavity manifests as merge source.

## Live ports

| Service | Port | URL |
|---------|------|-----|
| v3 UI | 3000 | http://127.0.0.1:3000 |
| Orchestrator | 8001 | http://127.0.0.1:8001 |
| Vulkan LLM | 8080 | http://127.0.0.1:8080 |

## One-command boot

```bat
C:\realai\start_v3_stack.bat
```

Opens stack: Vulkan → orchestrator → UI from `C:\realai\apps\frontend`.
