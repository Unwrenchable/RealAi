# Phase 3 parks (2026-09-26)

Grep-first moves onto this shelf. No dest-empty shim: `rg` found no live
`import` of these paths. Gold was not relocated. Rollback is `git mv` back.

| Shelf name | Was | Why |
|------------|-----|-----|
| `realai__plugins__abilities` | `realai/plugins/abilities` | Not in `FIRST_PARTY`. Zero `realai.plugins.abilities` / `plugins.abilities` imports. 16 modules byte-identical to `realai/plugins/rackup_coach/abilities` (live coach also has `player_card_sync.py`). Coaches not touched. |
| `realai__modules__torch_nn` | `realai/modules/*.py` except `__init__.py` | Torch `nn` dump. Zero hive imports. Shim `realai/modules/__init__.py` stays. |
| `realai__modules__desktop_unique` | `realai/modules/desktop_unique` | Partial twin. Catalog and hive use product-root `modules/desktop_unique`. |
| `realai__modules__self_improvement` | `realai/modules/self_improvement` | Broken relative-import dump. Hive uses `realai.self_improvement` → `realai.core`. |
| `realai__modules__training` | `realai/modules/training` | README only. Living entry is `core/training`. |
| `realai__apps` | `realai/apps` | Incomplete nest (vscode has no `package.json`). Zero `realai.apps` imports. |
| `apps__frontend` | `apps/frontend` | Slim twin of product-root `frontend/` (same npm name `realai-frontend`). |
| `abilities__realai` | `abilities/realai` | Wrong-level nest inside the ability package. Zero `abilities.realai` imports. |
| `agents__realai` | `agents/realai` | Wrong-level nest. `realai/agents/` was not restored. |
| `apps__fusion-ui` | `apps/fusion-ui` | Loser twin. `:8001` serves product-root `fusion-ui/`. |
| `realai__fusion-ui` | `realai/fusion-ui` | Loser twin. `script.js` matched `apps/fusion-ui`, not product root. |

Kept in place: `realai/abilities/` (authority note + `registry.json`), `realai/modules/__init__.py`, `realai/modules/organs/README_PARKED.md`, root `core/`, root `plugins/`, product-root `fusion-ui/`, `apps/vscode/webview/console.html`.
