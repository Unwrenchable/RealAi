# Where to search for agent / agent-tools gold

## Short answer

| What you asked | Verdict |
|----------------|---------|
| `C:\Users\tsmit\realai\agent-tools\agent-tools-main` | **Hollow shell** — almost no source left. Still register for gold hunt. |
| `agents` (git + else) | **Authority `C:\realai\agents` is live** (agentx 68 agents). Users/GitHub are overlap + extras. |

Full machine JSON: `scan_results/agent_tools_gold_map.json`

---

## Priority search order (best first)

### 1. Authority — already live (start here)

| Path | Gold |
|------|------|
| `C:\realai\agents\` | Agent markdowns, templates, tools, runtime planner |
| `C:\realai\agents\agentx\` | **Live hive**: `agents.json` (~68 agents), access_profiles, agency_import |
| `C:\realai\agents\tools\` | browser.ts, web-search.ts |
| `C:\realai\agents\runtime\` | planner.ts |
| `C:\realai\realai\hierarchical_agent_gold\` | Staged Desktop hierarchical agents |
| `C:\realai\recovered\from_desktop\realai-orchestration\` | Multi-agent orchestrator gold |
| `C:\realai\recovered\from_desktop\realai_agent\` | RISE / supervisor gold |

**Git (authority):** `C:\realai` → `origin https://github.com/Unwrenchable/RealAi`

### 2. Your path — agent-tools (mostly missing source)

| Path | Reality |
|------|---------|
| **`C:\Users\tsmit\realai\agent-tools\agent-tools-main`** | Wrapper: `.vscode/mcp.json`, `agent_tools.egg-info`, empty-ish `registry/` + `ui/` (only package-lock). **No `.py` source.** |
| `C:\Users\tsmit\realai\agent-tools-main` | Nested dup of same hollow tree |
| `C:\Users\tsmit\realai\archive\agent-tools-main` | Better: has **`.agentx`** (same `agents.json` size as authority — already promoted) |
| `C:\Users\tsmit\realai_historical_backups\...\agent-tools-main` | **Best recovery clue**: `__pycache__` only (`.pyc` for cli, dashboard, executor, importer, models, registry, runtime). Source deleted. |
| `C:\Unwrenchable\agent-tools` | Thin stub (empty AGENTS.md + 1 doc) |

**What agent-tools *used* to contain** (from `agent_tools.egg-info/SOURCES.txt`):

```
agent_tools/cli.py, dashboard.py, executor.py, importer.py, models.py, registry.py, runtime.py
agent_tools/engine/{executor,loader,logger,memory,router,test_harness}.py
agent_tools/providers/{anthropic,groq,local,openai,realai,router}.py
agent_tools/tooling/{crypto,filesystem,http,registry,solana}.py
agent_tools/data/{access_profiles,agents}.json
tests/…
```

→ Self-improve target: **recover agent_tools source from .pyc or GitHub history**, not re-copy the hollow folder.

### 3. agents trees (git + local)

| Path | Notes |
|------|--------|
| `C:\Users\tsmit\realai\agents` | Overlaps authority (agent.md, bootstrap, coder.agent.json, devops_agent.ts, …). **No agentx subdir here.** |
| `C:\Users\tsmit\realai-clean\agents` | Same class of docs |
| `C:\Users\tsmit\Documents\GitHub\realai` | **Git clone** of product (no separate `agents/` hit at probe; whole repo gold) |
| `C:\Users\tsmit\realai` git | `origin https://github.com/Unwrenchable/realai.git` |
| `C:\Users\tsmit\OneDrive\Desktop\realai_agent` | Hierarchical agent (already staged) |
| `C:\Users\tsmit\OneDrive\Desktop\realai-orchestration` | Orchestrator pool (already staged) |

### 4. Runtime / game agent surfaces

| Path | Notes |
|------|--------|
| `C:\Users\tsmit\.agentx` | Runtime dir (may be empty/thin) |
| `C:\Users\tsmit\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS\.agentx` | Game-side agentx |
| `...\ATOMIC-FIZZ...\backend\realai` | Overseer/NPC engines (already staged → `plugins/atomic_fizz_realai`) |

---

## What NOT to waste time bulk-merging

- Hollow `agent-tools-main` with only locks / egg-info / pycache
- Duplicate nested `agent-tools/agent-tools-main/agent-tools-main`
- Identical `agents.json` already in `C:\realai\agents\agentx`
- `node_modules` under any agents UI

---

## Recommended next gold actions

1. **Decompile or git-history recover** `agent_tools/*.py` from historical `.pyc` or `Unwrenchable/RealAi` / `realai` git history  
2. Search GitHub: `Unwrenchable/realai` and any `agent-tools` repo for the SOURCES.txt file list  
3. Keep using **`C:\realai\agents\agentx`** as authority hive  
4. Wire staged **hierarchical_agent_gold + orchestration_gold** when multi-agent LIVE path is ready  

---

## Quick copy-paste search list

```
C:\realai\agents
C:\realai\agents\agentx
C:\Users\tsmit\realai\agent-tools\agent-tools-main
C:\Users\tsmit\realai\archive\agent-tools-main
C:\Users\tsmit\realai_historical_backups\realai_versions_20260612\agent-tools-main
C:\Users\tsmit\realai\agents
C:\Users\tsmit\Documents\GitHub\realai
C:\Users\tsmit\OneDrive\Desktop\realai_agent
C:\Users\tsmit\OneDrive\Desktop\realai-orchestration
C:\Users\tsmit\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS\.agentx
C:\Users\tsmit\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS\backend\realai
```
