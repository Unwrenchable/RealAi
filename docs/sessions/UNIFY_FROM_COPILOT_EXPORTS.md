# Unification picture from Copilot exports (2026-09-02)

Sources read:

| Path | What it is | Signal |
|------|------------|--------|
| `C:\CopilotChats_MD\.md` | One **~41.5 MB** Windows Copilot Activity History dump (~1.5M+ lines) | Dense RealAI history (≈51k “RealAI” hits) mixed with export how-tos + Atomic Fizz noise |
| `...\670fbd84-….zip` (**176 MB**) | Grok/xAI account export; already extracted beside the zip | Same payload as the extracted folder |
| `...\prod-mc-asset-server\` | Contains **only** `_` (no other sibling files inside that folder) | UUID attachment blob store |
| `...\prod-mc-asset-server\_\` | **388 UUID folders**, each with a nameless `content` blob | Chat/upload attachments — craft, API, missions, catalogs, deploy configs, plus junk |
| `...\prod-grok-backend.json` | **51 MB**, **162** conversations | Grok chat titles + threads (Voice Lab, Hive, LoRA, unification, etc.) |
| `prod-mc-auth-mgmt-api.json` / `prod-mc-billing.json` | Auth/billing metadata | **Do not promote** (PII / irrelevant) |

**Note:** Explorer paths like `….zip\ttl\30d\…` are the zip-as-folder view. Content matches the extracted tree; there is no extra hidden tree beyond `_` + the three JSON sidecars.

Indexed artifacts: `docs/sessions/copilot_asset_index.jsonl` (171 high-signal blobs).  
Live Hive snapshot: `docs/sessions/live_tools.txt` (113 tools).

---

## 1. Development arc (complete picture)

What the dumps say RealAI was becoming, in order:

1. **Local provider bot** — stop speaking as Grok; RealAI owns inference + voice (Kokoro/Fish/XTTS).
2. **Archive / quarantine hygiene** — park mega-trees to `D:\`, keep `C:\RealAI-clean` as product.
3. **Vulkan + orchestrator ops** — `:8080` model, `:8001` hive, context overflow fights.
4. **Hive command surface** — walk / deep-promote / promote / heal / coverage (many *invented* names failed live_exec).
5. **Capability Manifest v3** — one-pager vision: `/v1/*`, agents, organs, Fusion UI, **VS Code extension**, training flywheel, Universe Mode.
6. **44 Synthetic Organs** — cognitive plugin taxonomy (maps to `modules/organs`).
7. **Voice lab** — local TTS/STT under `C:\models\checkpoints_lora\…`.
8. **Quarantine reconstruction / gold assembly** — `ability_matrix`, era maps, promote eval.
9. **Hive CLI vs Craft** — `realai` = hive operator; Craft becomes `realai craft`.
10. **Dual-root schizophrenia** — `C:\RealAI-clean` vs nested `C:\RealAI-clean\realai` registries.
11. **VS Code Console (now)** — Phase I: console UI + ability dock on living Hive (`apps/vscode` 1.2.x).

**Today’s tip of tree:** product home `C:\RealAI-clean`, Hive live, Console extension, session map in `docs/sessions/PHASES.md`.

---

## 2. Living capability surface (what RealAI can do *now*)

### Abilities (catalog IDs in `abilities/` / honesty map)

Core LLM / media:

- `chat_completion`, `text_generation`, `code_generation`, `code_execution`, `embeddings`
- `image_generation`*, `video_generation`*, `image_analysis`*
- `audio_transcription`*, `audio_speech`*, `voice_streaming`*, `translation`
- `web_research`, `task_automation`

(*Hive marks several as `partial:*` until backends are fully wired.)

Product / ops:

- `desktop_lambda_{chat,image,video,advanced}`, `overmind_runner`, `code_engineer_agent`, `code_engineer_cli`
- `deep_promote`, `hierarchical_specialists`, `approval_store`, `device_selector`
- `harden_repos`, `rollout_all_repos`, `quarantine_reconstruct`
- `plugin_system`, `memory_learning`, `self_reflection`, `knowledge_synthesis`, `multi_agent`
- `game_world`, `organs_hive`, `observability_self_improve`
- `local_inference`, `training_pipeline`, `lora_adapters`, `kilo_recovery`
- `frontend_ui`, `cli_surface`, `hominis_enterprise`

RackUp / coach (game-economy plugin):

- `coach`, `shot_of_the_day`, `rating_*`, `tournament`, `ledger_audit`, `matchmaking`, `hall_context`, …
- `web3_integration`, `business_planning`, `therapy_counseling`

### Live Hive (verified this session)

| Surface | Count / status |
|---------|----------------|
| `GET /v1/capabilities` | **58** |
| `GET /v1/tools` | **113** |
| `GET /v1/agents` | **68** |
| Hive core roles | overseer, coder, architect, analyst, memory, governor, router |
| Orchestrator | `:8001` OK |
| Vulkan | `:8080` OK |

Representative **tool families** (see `live_tools.txt` for full list):

- Workspace: `workspace_list|read|grep|write`
- Heal: `self_heal_*`, `self_extend`, `self_repair`, `system_scan`
- Hive/craft: `hive_*`, `craft_*`, `multi_agent_run`, `orchestration_surface`
- Voice: `voice_health|inventory|speak|listen`
- Recovery/LoRA: `recovery_status`, `list_lora_adapters`, `training_status`
- Surfaces: `agents_surface`, `modules_surface`, `repo_surface`, `plugins_surface`, `core_surface`
- Brains: `omnibrain`, `world_brain`, `overseer`, `organs_task`
- Ability mirrors: `ability.<id>` for most catalog entries
- Editor-like: `read_file`, `list_dir`, `search_replace`, `run_terminal_command` (bridge)

### VS Code Console (1.2.x)

- UI = `console.html` aesthetic (rail + feed + **ability dock**)
- Dock tabs: Abilities / Tools / Agents (live catalog)
- Deterministic: `/phase`, `/patches`, `/repo`, **smoke**
- Chat: stage + workspace context; tools-on only for operator `/…` and `$…`

---

## 3. Gaps from Copilot history (named but not fully living)

These `ability.*` names appear in the Copilot dump but are **not** in the living catalog IDs (or only partially covered by other tools):

| Missing / aspirational | Intent | Living substitute |
|------------------------|--------|-------------------|
| `walk_root`, `organize_repo`, `deep_unify_walk` | Repo walk / unify | craft `/list|/grep`, scanners, quarantine scripts |
| `promote`, `curated_promote`, `deep_promote_scan`, `deep_promote_wire` | Promote gold | `deep_promote`, `scripts/curated_promote.py`, self-heal promote queue |
| `self_heal`, `self_heal_loop`, `self_heal_cycle`, `self_heal_promote` | Heal loops | `self_heal_*` tools + `realai-heal` / self-heal status |
| `plugin_discover`, `plugin_merge`, `plugin_promote`, `plugin_registry_build` | Plugin registry | `plugin_system`, `plugins_surface` |
| `world_model_ingest|expand|merge|promote` | World model | `world_brain`, world endpoints where present |

**Rule:** Copilot often *invented* `/exec walker.scan` style names that failed live_exec. Treat dump names as **specs**, not registry truth. Wire only after a real module exists.

---

## 4. What the asset export is good for

Not a repo — **UUID attachment blobs**. Promote by **diff**, never blind overwrite.

### P0 (diff / archive)

| Blob theme | Why |
|------------|-----|
| Craft chat / 7-phase dispatcher (`37637a47…`, `103f7915…`) | Compare to `realai/cli/craft.py` |
| Unification mission prompt (`084c968b…`) | Ops cycle: doctor/gaps/heal/organs |
| API server dump (`2e83ac4c…`) | Diff vs `realai/api_server.py` |
| Historical ability catalog (~2026-08-24, ~48% coverage) | Archaeology only — living catalog is ~91% |
| Model registry YAML (`27fbf093…`) | Diff vs `models.yaml` |

### P1

- SAM/Lambda template, Render service YAML, Vulkan start `.bat`
- Agent manifest JSON — diff vs `agents/agentx/agents.json`
- Path lists of old roots (`C:\realai\…`) for `REALAI_EXTRA_READ_ROOTS`

### Do not promote

- `prod-grok-backend.json` wholesale (huge chat dump)
- Auth/billing JSON (PII / secrets-adjacent)
- Memecoin/Solana App Builder UI, pnpm lockfiles, terminal paste logs
- Overwriting current `ability_catalog` with older export

---

## 5. Unify RealAI “with all it’s capable of” — practical plan

### A. Single product contract (docs + env)

1. **One home:** `REALAI_HOME=C:\RealAI-clean`, workspace = cwd / open folder.  
2. Keep nested `realai/` as the **Python package**, not a second product root.  
3. Document verified slash + CLI + HTTP in one place (`ABILITIES.md` + this file).

### B. Ability honesty → Console dock

1. Drive Console **Abilities** tab from `GET /v1/capabilities` + `ability.*` tools (already).  
2. Add status badges LIVE / PARTIAL / STUB from `realai/ability_catalog.py`.  
3. Smoke button already batches health/hive/tools/agents/abilities — keep green.

### C. Close high-value gaps (code)

| Priority | Work |
|----------|------|
| 1 | Map Manifest “44 organs” → `modules/organs` packages; expose missing ones as tools |
| 2 | Promote-path: one `deep_promote` UX in Console (scan → wire → queue) using existing tools |
| 3 | World-model: surface `world_brain` + any `/v1/world/*` in dock |
| 4 | Voice: start Voice Lab `:8890` so Console/Hub Voice chip goes green |
| 5 | Partial media abilities: wire or clearly mark stub in dock |

### D. Mine dumps without polluting the tree

```text
docs/sessions/
  UNIFY_FROM_COPILOT_EXPORTS.md   ← this report
  copilot_asset_index.jsonl       ← 171 scored blobs
  live_tools.txt                  ← live tool names
  excerpt_capability_manifest_head.md
```

Optional next: curated copy of P0 blobs into `scan_results/from_copilot_export/` then `scripts/curated_promote.py --dry-run`.

---

## 6. Quick reference — how to *use* the full stack today

```bat
realai-stack
realai-health
```

VS Code: **RealAI: Open Console** (`Ctrl+Shift+A`)

- Dock → Abilities / Tools / Agents (click to run)
- `/phase` `/patches` `/repo` / smoke
- Operator: `/tools` `/hive` `/heal` `/lora` `/agents` `/multi …`
- API: `GET /v1/capabilities|tools|agents` · `POST /v1/tools/execute` · `POST /v1/multi-agent/run` · `POST /v1/abilities/run`

---

## 7. Combined “what to do” (after reading the zip + `_` + Copilot)

Yes — the zip/`prod-mc-asset-server` tree **has been read** (zip ≡ extract; asset-server ≡ `_` blobs + Grok JSON titles). Combined with living Hive:

### Do now (highest leverage)

1. **Keep using living Hive + Console** as the operator surface (don’t rebuild from exports).  
2. **Diff P0 blobs → tree** (craft, mission prompt, API server, model YAML) into `scan_results/from_copilot_export/` then curated promote.  
3. **Reconcile ability names** from Copilot (`walk_*`, `self_heal_loop`, `world_model_*`, plugin_*`) → existing tools or mark STUB in catalog.  
4. **RealAI Voice Lab (provider-level, not Grok)** — `python -m realai.voice.lab_server` / `bin\realai-voice.cmd` on `:8890`, provider id `realai-voice`, weights under `C:\models\checkpoints_lora`.  
5. **Single-root env** — see `docs/REPO_LAYOUT.md` (`REALAI_HOME=C:\RealAI-clean`).  

**Executed 2026-09-02:** P0 blobs → `scan_results/from_copilot_export/`; alias map → `docs/ABILITY_ALIASES.md`; Voice Lab started as `realai-voice`; Console 1.2.2 shows LIVE/PARTIAL badges + honesty %.

### Grok backend conversation themes to treat as backlog (titles)

Voice Lab · Hive live exec · Unification / self-heal · Abilities (local inference/training/self-improve) · LoRA/Unsloth OOM · Craft/dispatcher · Plugins (LoRA/autogui/tesseract) · Branch recovery · Fusion UI port · AMD Vulkan llama setup · Unified hive-mind repo.

### Skip

Auth/billing JSON · memecoin/Solana App Builder UI · wholesale `prod-grok-backend.json` import · older ability catalog overwriting today’s ~91% map.

---

## Bottom line

- **Copilot `.md`** = narrative + Manifest + failed/invented commands + dual-root diagnosis.  
- **Zip / `prod-mc-asset-server`** = only the `_` attachment store (+ sidecars). Already indexed; no extra folders inside asset-server beyond `_`.  
- **`prod-grok-backend.json`** = 162 Grok chats (many RealAI ops titles) — mine selectively, don’t dump into the repo.  
- **Living RealAI-clean** already has the real surface: **58 caps, 113 tools, 68 agents, organs, heal, LoRA, Console**.  
- Unification work is **reconcile names, close PARTIAL stubs, promote P0 diffs, keep one root** — not rebuild from Copilot/Grok prose.
