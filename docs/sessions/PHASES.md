# RealAI development phases (from Grok sessions)

Read this to understand **where development has been**.  
Session ids point at live folders under `~\.grok\sessions\` - see [`catalog.json`](catalog.json) for absolute `session_dir` paths.

**Current tip of product work:** Phase J - Any-repo full-stack Hive (Chat agents dispatch + foreign workspace + `/console` 1.2.10). Phase I Ultimate Console **landed** at `realai-vscode@1.2.10`.

---

## Phase A - Legacy mega-repo & craft (2026-07-11 → 2026-08-07)

**Lane:** `realai-core` @ `C:\realai`  
**Theme:** DDS scanners, unification boundary, craft/Vulkan chat, branch `unification/ultimate-all`.

| Date | Session title | Last turn / outcome |
|------|---------------|---------------------|
| 2026-07-11 | RealAI Codebase Software Engineering at C:\realai | Craft streams Vulkan tokens; `/improve` ends doctor loop |

**Session id:** `019f51fd-f6c4-7451-a683-135d57e0b00f`

---

## Phase B - Land in RealAI-clean (2026-08-08 → 2026-08-13)

**Lane:** `realai-core` @ `C:\RealAI-clean`  
**Theme:** Move scripts into clean tree, locked VFS / external copy limits, craft tools, architect mode, GGUF vs safetensors.

| Date | Session title | Last turn / outcome |
|------|---------------|---------------------|
| 2026-08-08 | Move realai Scripts to RealAI-clean Fix | Curated settled; nest wire applied; promote_actionable 0 |
| 2026-08-08 | RealAI-clean Locked VFS External Repo Copy Limits | sdk-ts promoted; craft `/at` gold tools live |
| 2026-08-13 | Add Missing tool_architect_mode Function to craft.py | Runtime weights are `.gguf`; train as `.safetensors` first |

---

## Phase C - Hive / Vulkan / MCP inventory (2026-08-22 → 2026-08-24)

**Theme:** Bring Hive online, inventory/unify, MCP doctor, context overflow, agent wiring.

| Date | Session title | Last turn / outcome |
|------|---------------|---------------------|
| 2026-08-22 | RealAI Vulkan Hive State Mission Wait | (in progress / wait state) |
| 2026-08-22 | RealAI Hive Inventory Unify and MCP | Job A maps + Job B MCP doctor healthy |
| 2026-08-23 | RealAI Unification Inventory Map Exploration | explore |
| 2026-08-23 | Plugin vs Ability Classification Unification Plan | plan |
| 2026-08-23 | UNIFY_PLAN MessageBus Pin + RackUp Abilities | Gold specialists in `core/agents`; promote smoke green |
| 2026-08-23 | Inspect RealAI Hive Recovery and Module Fixes | hive 9/11, `/v1/tasks` live |
| 2026-08-23 | Imports exploration unique high-value unpromoted code gems | explore |
| 2026-08-23 | RealAI docs/results/logs value exploration | explore |
| 2026-08-23 | Deep Nest Exploration Beyond Exportable Salvage | explore |
| 2026-08-23 | RealAI Authority Destinations Deep Promote Map | explore |
| 2026-08-24 | Fix Missing GGUF and Selfheal Script Parse | Hive mode live: 7 agents wired, delegation OK |
| 2026-08-24 | Fix Hive 8192 Context Overflow | Retargeted hive model to 7B / 16k context |

---

## Phase D - Abilities, Atomic Fizz gold, gap fill (2026-08-27)

**Theme:** Fusion UI fix, ability wiring coverage, pull gold from Vault-77 concepts into RealAI-clean (without treating Vault as product home).

| Date | Session title | Last turn / outcome |
|------|---------------|---------------------|
| 2026-08-27 | Fix Fusion UI index.html DOM mismatch | :8001 up; lora_root `C:\models\checkpoints_lora` |
| 2026-08-27 | RealAI Ability Wiring & Atomic Fizz Gold | 90.5% coverage - 10 real gaps left |
| 2026-08-27 | RealAI Ability Gaps Status Audit | audit |
| 2026-08-27 | RealAI Gap Fill From ATOMIC-FIZZ Vault | gap fill |
| 2026-08-27 | Scan Overseer Repos for Omnibrain MCP Wiring | scan |

**Note:** Separate Vault-77 *repo* session exists under lane `adjacent-other-repo` (not product).

---

## Phase E - Workspace bind, multi-agent, CLI (2026-08-28)

| Date | Session title | Last turn / outcome |
|------|---------------|---------------------|
| 2026-08-28 | RealAI Workspace Bind & Live Orch Fix | ONLINE orch :8001; `/multi` planner/worker/critic |
| 2026-08-28 | RealAI Hive Multi-Agent Vulkan Autostart Fix | Hive CLI: route/run/gpu/world + `CLI_TREE.md` |
| 2026-08-28 | Explore RealAI CLI surfaces and hive gaps | explore |
| 2026-08-28 | Fix RealAI CLI not recognized *(tooling lane)* | Editable install; bare `realai` on PATH |

---

## Phase F - Quarantine restore, bot identity, stack wiring (2026-08-30 → 2026-08-31)

| Date | Session title | Last turn / outcome |
|------|---------------|---------------------|
| 2026-08-30 | RealAI Quarantine Restore and Stack Repair | Easy `/tools` + aliases; compact hive/heal/lora replies |
| 2026-08-30 | RealAI Bot Identity Pipeline Routes Exploration | explore |
| 2026-08-30 | RealAI Stack Abilities Inventory Orch Wiring Gaps | inventory |
| 2026-08-30 | Orchestrators Nest Inventory Unify Plan | plan |
| 2026-08-31 | Quarantine Restore, Models Unify, Worker Wire | Park via `park_archive_to_d.ps1` |
| 2026-08-31 | Nested Python Package Promotion Plan | plan |

---

## Phase G - Voice Lab (2026-08-31)

**Lane:** `realai-voice` @ `C:\RealAI-clean\realai\voice`

| Date | Session title | Last turn / outcome |
|------|---------------|---------------------|
| 2026-08-31 | RealAI Local Voice Lab Hive Rewrite | Voice Lab up on :8890 - realai-voice healthy |

**Session id:** `01a057f4-d535-7972-bdc6-5e03815542c8`

---

## Phase H - VS Code extension Dev Chat (2026-09-01)

**Lane:** `realai-core` @ `C:\RealAI-clean`  
**Theme:** Make `apps/vscode` a real workspace-aware IDE chat against Hive `:8001`.

| Date | Session title | Last turn / outcome |
|------|---------------|---------------------|
| 2026-09-01 | RealAI VS Code Extension Local Fixup | 0.5.0 streaming/context fixes |
| 2026-09-01 | RealAI Chat Context Injection & VS Code APIs | context / API exploration |

**Session id:** `01a05fdd-36c0-7be1-9af6-4a0552c2a30a`

---

## Phase I - RealAI Ultimate VS Code + Console home (2026-09-01 → 2026-09-08) — LANDED

**Lane:** `realai-core` @ `C:\RealAI-clean`  
**Theme:** One Copilot/Grok-class surface — Hub + Console + browser `/console` parity; Hive is the only browser origin.

### Exit criteria (met)

- Extension **`realai-vscode@1.2.10`** (Hub + Console + LM provider vendor `realai`)
- Browser home: **`http://127.0.0.1:8001/console`** (Next `:3000` redirects; Agents UI watch-only)
- Speech: browser SPEAK → only `:8001/v1/audio/speech` (XTTS/Laura via internal Voice Lab; no `:8890` in DevTools)
- Ops dock: live `/v1/abilities` + tools + agents; Hive tab runs via `/v1/agents/run`
- Slash: `/phase` `/repo` `/patches` `/tools` `/agents` `/heal` `/caps` `/multi` `/help`
- Defaults: Hive `:8001`, model `realai-hive`; voice branded `realai-tts`

### What was keeping the tip on “Phase I”

The tip line in this file lagged at `1.2.5`. Console `/phase` reads **Current tip of product work** from this doc — updating the tip (not a hidden gate) advances the stage pill.

---

## Phase J - Any-repo full-stack Hive (2026-09-08 → now)

**Theme:** RealAI as standalone provider everywhere — foreign workspaces, Chat agents that actually dispatch, terminals with `REALAI_HOME` / `REALAI_WORKSPACE`.

### In progress / acceptance

| Gate | Status | How to clear |
|------|--------|----------------|
| Install `realai-vscode-1.2.10.vsix` + reload | user | Extensions → Install from VSIX |
| Chat pick **RealAI → coder (full stack)** or **RealAI Agent:*** (not Copilot model) | user | Agents UI shows dispatch→complete |
| Foreign repo: open non-`RealAI-clean` folder; Console knows FOREIGN + full-stack | verify | `/phase` + context pack |
| RealAI terminal profile / `realai` / `realai-code` in any cwd | verify | Terminal → RealAI profile |
| Browser SPEAK: DevTools shows **zero** `:8890` | pending accept | Speak from `/console` |
| Tip + catalog stay current after milestones | ongoing | edit this file; `refresh_catalog.ps1` |

### Phase J done when

1. Daily coding path is RealAI Chat coder/agent with visible Hive runs.
2. Any-repo (CLI + VS Code + `/console`) is the default story (`ANY_REPO.md` + extension hostMode).
3. Speech acceptance checked off.
4. Tip advances to **Phase K** (next named milestone — e.g. Universe Mode depth, 64k-stable Agent mode, or ability honesty ≥ target).

---

## Not RealAI product phases (do not mix into the timeline above)

| Lane | Session | Why excluded |
|------|---------|--------------|
| `unrelated` | Fix NestJS Express Types on Render Node | Rack_em_up NestJS/Render typings |
| `adjacent-other-repo` | RealAI Omniverse Engine Vault-77 Heals | Separate game/vault repo; Omniverse scaffold only |

---

## How to continue cleanly

1. Prefer working in **`C:\RealAI-clean`** so new sessions land in the primary root; for other repos use foreign/any-repo mode (`REALAI_HOME` + workspace cwd).
2. After major milestones, update **Current tip** in this file + skim `catalog.json`.
3. Refresh the catalog: `powershell -File docs/sessions/refresh_catalog.ps1`
4. `/phase` in Console always reflects the tip line above — bump the tip when a phase lands.
