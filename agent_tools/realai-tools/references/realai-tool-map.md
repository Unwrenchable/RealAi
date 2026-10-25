# RealAI Repo Tool Hotspots

Use these paths when building or invoking repo-wide tools inside the RealAI monorepo.

**Authority:** `C:\RealAI-clean` (`REALAI_HOME`). Do not guide operators toward `.blackbox/` skill roots.

**Fence for RackUp:** If the open root is `Rack_em_up` / Nest, stop. Use HTTP `POST {REALAI_BASE_URL}/v1/plugins/rackup-coach`. Do not vendor hive paths into RackUp.

## Primary Skill & Tool Locations
- `agent_tools/` - runtime tools and this `realai-tools` pack
- `abilities/` - hive abilities (including RackUp-facing under `abilities/rackup/`)
- `realai/agent_tools_gold/` - gold / reference tool copies
- `realai/plugins/` and `plugins/` - plugin surfaces (e.g. `plugins/rackup_coach`)
- `realai/orchestration/` / `orchestrator/` - orchestration entry points
- `realai/abilities/` - nested ability packages inside the realai tree
- `scanners/` and `realai/scanners/` - cavity and spectrum scanners
- `modules/` - organs, advanced agents, training helpers
- `scripts/` - utility scripts
- `apps/vscode/`, `apps/frontend/`, `apps/api/`, `frontend/` - app surfaces

## Key Entry Points
- `orchestrator/` / `realai/orchestration/` / `realai/cli/`
- `apps/api/`, `apps/frontend/`, `apps/vscode/`, `frontend/`
- `providers/` and `models/` (do not scan weight dumps by default)
- `realai/` package (cli, memory, models, sdk, server, registry)

## Recommended First Tools to Wrap
1. Cavity scanners under `scanners/` / `realai/scanners/` (full / alt / tri)
2. Model manifest readers (realai-1.0, overseer, embed) — do **not** invent escrow/vision as LIVE
3. Repo tree generators that exclude archives, node_modules, checkpoints, and weight trees
4. Safe merge / phase helpers where present
5. Knowledge / memory store query wrappers around RealAI memory and registry surfaces
6. `provider_switch`, `memory_store`, `rating_update` framed as hive abilities

## Ignore Patterns for Repo-Wide Scans
Always exclude by default:
- `node_modules/`, `.venv/`, `venv/`, `__pycache__/`
- `.backup/`, `realai_historical_backups/`, `archive/`, `_parked/`, `_quarantine/`, `RealAI_Recovery_SAFE/`
- `D:\ARCHIVE` (and any ARCHIVE drive roots when scanning across volumes)
- `*.egg-info/`, `.pytest_cache/`, `.git/`
- Large binary / weight directories under `models/`, `weights/`, `hf/`, `checkpoints/`, `checkpoints_lora/`
- Secrets, `.env`, credential files — never copy into skill packs
