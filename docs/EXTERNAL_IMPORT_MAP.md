# External import map (host-side)

## Product sandbox (default)

When `home` and `workspace` both point at `C:\RealAI-clean`:

| Layer | Behavior |
|-------|----------|
| `realai.workspace.safe_under()` | Paths must stay under workspace **unless** EXTRA_READ |
| `safe_under_read()` | Workspace **+** `REALAI_EXTRA_READ_ROOTS` |
| `safe_under_write()` | Workspace **only** (writes never leave product tree) |
| `realai/cli/craft.py` | `/list` `/read` `/grep` use read; `/write` uses write |
| `v3_runtime_bridge` | File tools delegate to craft |

**`REALAI_ALLOW_EXTERNAL_READ` alone does nothing.**  
Roots must be listed in **`REALAI_EXTRA_READ_ROOTS`**.

### Opt-in external read (policy change — implemented, default-off)

```bat
set REALAI_EXTRA_READ_ROOTS=C:\realai;D:\realai_archives;C:\realai_recovery_;C:\RealAI_Recovery_SAFE;C:\realai_giant_hold;C:\realai_grok_export;C:\RealAi-unified;C:\Users\tsmit\realai;C:\Users\tsmit\realai_documents
realai
```

Or permanently for a session after `realai-stack`. Writes to those roots remain **denied**.

### Portable project mode (no EXTRA_READ needed)

```bat
cd C:\MyApp
realai
```

File tools operate on `C:\MyApp`. Product tools still use `REALAI_HOME`.

---

## External roots (host inventory 2026-08-08)

| Path | Status | Usefulness |
|------|--------|------------|
| `D:\realai_archives` | Exists — large multi-GB dumps | Curate only; do not bulk-copy |
| `C:\realai` | Full product-like tree (modules, plugins, server, core) | High — modules/plugins/server imported as snapshots |
| `C:\Users\tsmit\realai` | Alternate tree + vscode | VS Code source (corrupted `extension.ts` historically) |
| `C:\realai_recovery_` | **Best gold** — `agent_tools_gold`, `unique-modules`, packages | **Primary import source** |
| `C:\RealAI_Recovery_SAFE` | Flattened `C__…` path dumps | Hard to use; leave for forensic |
| `C:\realai_giant_hold` | Hold snapshots / large blobs | Index only |
| `C:\realai_grok_export` | Medium export | `realai/` package snapshot imported |
| `C:\RealAi-unified` | Many empty shells | Low |
| `C:\Users\tsmit\realai_documents` | 9 contract markdowns | Imported → `docs/external_contracts/` |
| `C:\Users\tsmit\realai_good` | Empty shell | Skip |

### Novel basenames (vs living clean trees)

| Source | Novel basenames | Notes |
|--------|----------------:|-------|
| `agent_tools_gold` | 15 | filesystem/http/crypto providers, runtime |
| `unique-modules` | 25 | gold scanners + tools overlap |
| `C:\realai\modules` | ~0 | Already in living clean |
| `C:\realai\plugins` | ~0 | Overlap with living |
| archives (D:) | hundreds mangled | Not for bulk promote |

---

## Already living in RealAI-clean

- agents, world-model, self-heal, organs, training, plugins, recovered history  
- denser core Python than `C:\Users\tsmit\realai`  
- `apps/vscode/` reconstructed (`extension.ts` + contributes, compiles)  
- `apps/frontend/`, `packages/design-system/`, `apps/fusion-ui/`

## Host-imported snapshots (`imports/external/`)

| Folder | Source |
|--------|--------|
| `agent_tools_gold/` | `C:\realai_recovery_\agent_tools_gold` |
| `unique-modules/` | `C:\realai_recovery_\unique-modules` |
| `recovery_agents/` | `C:\realai_recovery_\agents` |
| `recovery_plugins/` | `C:\realai_recovery_\plugins` |
| `recovery_packages/` | `C:\realai_recovery_\packages` |
| `recovery_training/` | `C:\realai_recovery_\training` |
| `C_realai_modules/` | `C:\realai\modules` |
| `C_realai_plugins/` | `C:\realai\plugins` |
| `C_realai_server/` | `C:\realai\server` |
| `grok_export_realai/` | `C:\realai_grok_export\realai` |
| `vscode_snapshot_*` | users/recovery vscode trees |

These sit **inside** the workspace, so product-mode `/read` can see them without EXTRA_READ.

### Re-run / extend imports

```bat
python scripts\import_external_trees.py
python scripts\import_external_trees.py --apply
python scripts\import_external_trees.py --id agent_tools_gold --apply --force
```

Promote individual files into living paths with:

```bat
python scripts\curated_promote.py --dry-run
```

---

## Claimed missing vs reality

| Claim | Reality |
|-------|---------|
| VS Code extension missing | Living `apps/vscode` restored; raw snapshots under `imports/external/vscode_*` |
| UI mockups from realai_documents | Documents are ROC/RackUp contracts, not UI kits |
| realai_good modules | Empty |
| agent/tool gold | Now under `imports/external/agent_tools_gold` (+ unique-modules) |
| Multi-GB archives auto-unify | Still manual curation — importer skips huge blobs |

## What is intentionally not bulk-imported

- `D:\realai_archives\**` multi-GB  
- `C:\realai_recovery_\modules_runtime` (~1.3GB source-ish)  
- `C:\realai_giant_hold` large holds  
- `C:\RealAI_Recovery_SAFE` mangled flat dumps  

Promote from those only via allowlisted `curated_promote` entries after human selection.

---

## Living promotion status (2026-08-08)

### 1. `agent_tools_gold` → living (done)

| Path | Role |
|------|------|
| `agent_tools/` | Canonical import package (`import agent_tools`) |
| `realai/agent_tools_gold/` | Marker + mirror for deepen_cycle / ability catalog |

Orchestrator tools (via `v3_runtime_bridge` + `v3_orchestrator._run_tool`):

- `agent_tools_status` — gold package health + agentx counts  
- `agent_tools_list_agents` — merge agentx + gold agents  
- `agent_tools_list_profiles` — bridge profiles + gold safe/balanced/power  
- `agent_tools_assess` — gold assess when possible  
- `agent_tools_list_tools` — wired tooling (filesystem/http/crypto/solana)  
- `agent_tools_invoke` — invoke tooling under profile (`dry_run` default **true**)

Filesystem gold tool respects `safe_under_read` (workspace + `REALAI_EXTRA_READ_ROOTS`).

### 2. Diff snapshots → promote allowlist

```bat
python scripts\diff_imports_promote_allowlist.py
python scripts\diff_imports_promote_allowlist.py --apply-hints
```

Output: `scan_results/promote_allowlist_from_imports.json`  
(candidates with `novel` / `newer_or_fork` + curated_promote stub)

### 3. Archives policy (snapshots + EXTRA_READ only)

| Location | Policy |
|----------|--------|
| `imports/external/**` | Snapshots inside workspace (readable in product mode) |
| `D:\realai_archives`, `C:\realai_giant_hold`, `C:\RealAI_Recovery_SAFE` | **Do not bulk-copy**; set `REALAI_EXTRA_READ_ROOTS` for deep dives |
| Living promote | Only allowlisted small source files |

```bat
set REALAI_EXTRA_READ_ROOTS=D:\realai_archives;C:\realai_giant_hold;C:\RealAI_Recovery_SAFE;C:\realai;C:\realai_recovery_
```

### 4. sdk-ts recovery slice + craft `/at` (done)

Promoted from `imports/external/recovery_packages/sdk-ts/src`:

| File | Living dest |
|------|-------------|
| `envChatClient.ts` | `packages/sdk-ts/src/envChatClient.ts` |
| `registryClient.ts` | `packages/sdk-ts/src/registryClient.ts` |
| game/world modules (`*.js`) | `packages/sdk-ts/src/game/*` |
| recovery `index.ts` | **not** merged (kept living `RealAI` class) |

`packages/sdk-ts/src/index.ts` re-exports chat + registry clients.

Craft slash commands:

```
/at status
/at tools
/at agents [query]
/at profiles
/at assess <agent_id> [profile]
/at invoke <tool> [json_payload]     # dry_run true
/at invoke-live <tool> [json|path]   # dry_run false
```

Aliases: `/agent-tools`, `/gold`, `/agent_tools`.
