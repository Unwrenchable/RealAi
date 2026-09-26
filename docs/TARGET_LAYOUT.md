# Target layout vs live today

Moves are **rename + shim**, never copy-paste duplicates.

## Keep as-is (gold)

| Path | Why |
|------|-----|
| `realai/orchestration/v3_orchestrator.py` | Hive gold |
| `realai/orchestration/v3_runtime_bridge.py` | Bridge gold |
| `realai/core/self_builder.py` and siblings | Self-* gold |
| `realai/plugins/` | Plugin authority |
| `realai/ability_catalog.py` | Honesty map |
| `modules/organs/` | Organs hive |
| `apps/vscode/` | Console extension |
| `frontend/` | Next shell |
| `packages/design-system/` | UI kit |
| `scanners/` | Promote tools |

## Shims that must stay until imports are grepped clean

| Shim | Target |
|------|--------|
| `realai/v3_orchestrator.py` | `realai.orchestration.v3_orchestrator` |
| `realai/v3_runtime_bridge.py` | `realai.orchestration.v3_runtime_bridge` |
| `realai/self_builder.py` | `realai.core.self_builder` |
| `plugins/` | `realai.plugins` |

## Park (stop being on the mental map)

Move to `_quarantine/twins_YYYYMMDD/` or delete after a week on a park branch:

- `realai/realai/`, `realai/realai_repo/`, `realai/realai_sdk/`
- `realai/grok_export_realai/`, `realai/deep_nests/`, `realai/from_nests/`
- `realai/plugins/plugins/`, `realai/plugins/C_realai_plugins/`
- Root `layout.tsx`, `globals.css`, `Hey — I'm here..txt`
- Root `world_model.json` if `realai/world_model.json` is the copy Hive loads. Phase 4 left it: same sha256 as `realai/world_model.json`, but `abilities/repo_surface.py` still names the repo-root path and Hive gold does not open the JSON.
- Duplicate `start_*.bat` once `START_HERE.bat` + `scripts/` cover them. Phase 4 moved the bodies to `scripts/windows/` and left root forwarders (menu stays `START_HERE.bat`).

## Relabel

| Today | Should be |
|-------|-----------|
| `pyproject.toml` version `2.0.0` | `3.0.0` (hive product) |
| Root `AGENTS.md` (Grok sandbox) | `docs/foreign/GROK_APP_BUILDER_AGENTS.md` |
| New RealAI agent contract | `docs/AGENTS_REALAI.md` |
| `docs/architecture.md` (May 2026 JS engine) | stamp **historical** at the top |

## Do not create

- `v1/`, `v2/`, `v3/` directories
- A second `realai` git inside `realai/`
- `apps/desktop` if `desktop/` + `modules/desktop_unique` already hold the surface
