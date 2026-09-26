# Monorepo migration phases — Unwrenchable/RealAi

**Layout contract:** [`MONOREPO_TARGET_LAYOUT.md`](MONOREPO_TARGET_LAYOUT.md)
**Branch each phase merges into:** `live/realai-clean-20260911`
**Product home:** `C:\RealAI-clean`

Live stays runnable after every phase. A phase is one PR. Moves are `git mv` plus a dest-empty re-export shim when an import path still exists. Copy-paste duplicates are not a move.

This document is phase 0. It does not move, delete, or rewrite product code, and it does not absorb quarantine, recovery, backup, or unified dumps.

---

## Smoke checks (every phase that touches code)

Run from product home after the phase's PR is checked out. Do not start a second orchestrator if `:8001` is already healthy.

| Check | Command / request | Pass |
|-------|-------------------|------|
| Orch health | `GET http://127.0.0.1:8001/health` | 200, body identifies the v3 orchestrator |
| Orch import | `python -m realai.v3_orchestrator --help` | usage text, exit 0 |
| Gold import | `python -c "import realai.orchestration.v3_orchestrator as o, realai.orchestration.v3_runtime_bridge as b; print(o.__file__); print(b.__file__)"` | both paths end in `realai/orchestration/v3_*.py` |
| Shim still wired | `python -c "import realai.v3_orchestrator as s; print(s.main)"` | `main` resolves; no second copy of hive logic in the shim file |
| Plugins | `python -c "from realai.hive import hive_status, register_plugins; print(hive_status().get('ok')); print(register_plugins())"` | ok, plugins register (sample / rackup-coach / atomicfizz when those packages are present) |
| Organs | `python -c "from modules.organs import hive_status; print(hive_status())"` | `complete` true (snapshot expectation: organ_count 45) |
| Catalog | `python -c "from realai.ability_catalog import coverage_summary; print(coverage_summary())"` | prints without import error |
| Console twins | hash `apps/vscode/webview/console.html` and root `console.html` | identical bytes |
| Console route | `GET http://127.0.0.1:8001/console` | 200 HTML |
| Vulkan | `GET http://127.0.0.1:8080/health` | 200 when the GPU server is up. A down Vulkan box fails the stack smoke, not the import smoke |

Env the bats already set: `REALAI_HOME=C:\RealAI-clean`, `PYTHONPATH=C:\RealAI-clean;C:\RealAI-clean\realai`, `REALAI_VULKAN_BASE=http://127.0.0.1:8080`, `REALAI_API_BASE=http://127.0.0.1:8001`.

A phase that only edits `docs/` skips the port checks and still runs the import lines if the reviewer wants a baseline. Phase 0 (this PR) is docs-only: no smoke is required to merge it, and no server is started by it.

---

## Phase 0 — contract (this PR)

**Risk:** none to runtime. Docs only.

- Add `docs/MONOREPO_TARGET_LAYOUT.md` (target tree, inventory, wiring diagram).
- Add `docs/MONOREPO_MIGRATION_PHASES.md` (this file).
- Filesystem unchanged. Gold paths unchanged. Shims unchanged. `_quarantine/` unchanged.

**Done when:** a reader can name hive, bridge, console, fusion, plugins, and organs without opening a nested dump.

---

## Phase 1 — names and front door (docs and labels)

**Risk:** low. No import path changes.

Already done on live from earlier PRs (do not redo):

- `pyproject.toml` version `3.0.0`
- `docs/AGENTS_REALAI.md` and `docs/foreign/README.md` marking root `AGENTS.md` as the App Builder sandbox contract
- root `ARCHITECTURE.md` as the layout contract

Still open, docs-only unless a one-line README edit is included:

- README "Repo layout" points at `ARCHITECTURE.md` and this plan.
- Stamp `docs/architecture.md` historical at the top if the stamp is missing.
- Catalog rows whose only gold path is `C:\tools\realai` stay `PARTIAL` (`docs/LINEAGE.md`).

**Smoke:** import lines only.

**Stay put:** every directory.

---

## Phase 2 — park remaining nested dumps

**Risk:** medium if a hidden import still points into a dump. Low if the move is `git mv` into `_quarantine/` and a same-name shim is left only where `rg` finds importers.

**Scope (inside the product tree only):**

| From | To (new shelf folder, one date) |
|------|----------------------------------|
| `realai/orchestrator-default-run/` | `_quarantine/twins_<date>/realai__orchestrator-default-run` |
| `realai/agent-tools-orchestrator-default-run/` | same shelf |
| `realai/agents-orchestrator-default-run/` | same shelf |
| `realai/ai-orchestrator-default-run/` | same shelf |
| `realai/core_unify_20260830/` | same shelf |
| `realai/orchestration_gold/` | same shelf |
| `realai/realai-core/` | same shelf |
| `realai/realai-frontend/` | same shelf |
| `realai/exportable/`, `realai/v18/`, `realai/variants/` | same shelf, after `rg` shows no `import` |

Tooling already sketched: `scripts/park_nested_dumps.ps1` (see `docs/WIRING_PASS.md`). Extend it; do not invent a second copier.

**Already parked — do not move again:** `_quarantine/twins_20260921/*` (`realai__realai`, `realai__deep_nests`, `realai__plugins__plugins`, …) and `_quarantine/twins_20260924/realai__modules__organs`.

**Smoke:** full table. Confirm `import realai.orchestration.v3_orchestrator` still loads the gold file, not a file under `_quarantine`.

**Risk note:** `realai/orchestrator-default-run/` is about 11 MB. Reviewers should expect a large rename diff and a small logical change.

**Landed 2026-09-26** on shelf `_quarantine/twins_20260926/` (`realai__<name>`). `rg` found no live importer, so no dest-empty shim was left. `realai/scripts/exportable/` (hive nest index) was not this dump and stayed. Already-shelved `twins_20260921*` and `twins_20260924` were not moved again.

---

## Phase 3 — one import path per surface

**Risk:** medium. Grep first, then delete or shim the loser. Never delete gold.

Order:

1. **Abilities.** Authority is product-root `abilities/`. `realai/abilities/` is already an authority note. Grep `realai.plugins.abilities` and `realai/abilities` before touching the 17 Python files under `realai/plugins/abilities/`. If Hive loads those plugin-local modules, they stay as plugin code, not as a second ability tree.
2. **Agents.** Authority is product-root `agents/`. `realai/agents/` is already gone. Do not restore it from `_quarantine/twins_20260924/realai_agents`.
3. **Organs.** Authority is `modules/organs`. `realai/modules/organs` is a park note. The other files in `realai/modules/` (`linear_fused.py`, `pixelshuffle.py`, `rnn.py`, …) are a Torch-style dump, not organs. Park that dump in phase 2 or here only after grep shows no hive import.
4. **Core.** Authority is `realai/core`. Root `core/` stays as the compat package (`from core.orchestration` / `from core.plugins`).
5. **Plugins.** Authority is `realai/plugins`. Root `plugins/` stays as the `sys.modules` re-export.
6. **Console.** Authority is `apps/vscode/webview/console.html`. After any console edit, copy that file onto root `console.html` and fail the phase if hashes differ. Do not install or edit `realai/apps/vscode`.
7. **Fusion.** Authority is product-root `fusion-ui/`. `apps/fusion-ui/` and `realai/fusion-ui/` differ in `index.html` and `script.js` (only `config.js` matches). Diff them in the PR body. Park the losers only after confirming `:8001` serves product-root `fusion-ui/`. Do not replace the product-root files with the larger apps copy.
8. **Frontend.** Authority is `frontend/`. `apps/frontend/` and `realai/realai-frontend/` are twins (`docs/APPS_MAP.md`). Park later in this phase, not before phase 2's nest move.

Leave a dest-empty shim wherever an external launcher or `from <loser> import` still exists. A shim is about ten lines and a docstring that names the gold module. No logic.

**Smoke:** full table, plus `GET /console` and the console hash pair.

---

## Phase 4 — launcher and root-drawer tidy

**Risk:** low for Python, medium for operator muscle memory.

- Keep `START_HERE.bat` as the Windows front door. Point the other `start_*.bat` / `run_*.bat` files at it or move the extras under `scripts/windows/` with a one-line forwarder left at the root for the names `start_all.bat` and `start_orchestrator.bat` (those are cited by `docs/ORCH_8001_STATIC.md` and `docs/REPO_LAYOUT.md`).
- Root `world_model.json`: park only if Hive loads `realai/world_model.json` and a hash or load-path comment proves the root file is unused.
- `packages/core/` (empty npm package named `realai-core`): leave it, or remove it from `pnpm-workspace.yaml` in a JS-only PR. Do not put Python in it. Do not rename `realai/` to `packages/realai-core`.
- Root `src/`, root `package.json` (`app-builder-workspace`), and `vite.config.ts` stay. They are the foreign App Builder overlay. Folding them into `frontend/` or `apps/vscode/` is a separate product decision, not part of hive wiring.

**Smoke:** `start_orchestrator.bat` still reaches `python -m realai.v3_orchestrator` on `:8001`. Import lines. Console hash pair.

**Landed 2026-09-26.** `START_HERE.bat` stays the Windows menu and still calls the root names. Implementation bodies moved with `git mv` to `scripts/windows/` (`start_all`, `start_orchestrator`, `start_orchestration_worker`, `start_craft`, `start_gpu_chat`, `start_ui`, `start_realai_server`, `start_self_build`, `run_chat`, `run_selfheal`). Each of those root names is a one-line `call` forwarder, so `start_all.bat` still reaches `scripts\unified_stack.py` and `start_orchestrator.bat` still reaches `python -m realai.v3_orchestrator`. `start_stack.bat` and `start_realai.bat` were already aliases to `start_all.bat` and stayed. Root `world_model.json` stayed: sha256 `800980f8b4b3c476dc800753c348a17d289c3d5db683816cec534ce3ad83bb03` matches `realai/world_model.json`, but Hive gold does not open that JSON, and `abilities/repo_surface.py` still names the repo-root path, so unused was not proven. `packages/core/` stayed the empty npm package `realai-core` (no Python, still under `packages/*`). Root `src/`, `package.json`, and `vite.config.ts` were not folded.

---

## Phase 5 — promote from shelves (optional, file by file)

**Risk:** high if treated as a merge. Low if treated as a symbol diff.

Shelves are read-only until a single file beats live gold:

- `_quarantine/**`
- `recovered/`, `imports/`
- branches `recovery/*`, `local/*`
- `C:\RealAI-gold`, `C:\RealAI-clean-backup`
- `main` and any unified dump

Tool: `scanners/promote_gold.py`. Accept a file only when it beats the live gold file on size **and** unique top-level symbols, and the live file is not an intentional shim.

Prior deltas already recorded **zero promotions**:

- `docs/QUARANTINE_CONTENT_DELTA.md` — quarantine `ability_catalog.py` is a dump of symbols the live shim re-exports; organs `base.py` basename collision; do not replace shims.
- `docs/SHELF_CONTENT_DELTA.md` — `.before` orchestrator copies and `orphans/` stay parked.

**Smoke:** full table after each accepted file, not after a batch copy.

---

## Non-goals

Out of scope for this plan and for every phase above:

1. **No dump absorption.** Do not merge `recovery/*`, `local/*`, `main`, `C:\RealAI-gold`, `C:\RealAI-clean-backup`, `D:\RealAI-archive`, `recovered/`, or `imports/` onto `live/realai-clean-20260911`. Do not xcopy a shelf over the product tree.
2. **No second product tree.** Do not create `v1/`, `v2/`, `v4/`, `unified/`, or a nested `.git` under `realai/`.
3. **No gold relocation.** Hive, bridge, plugins, organs, fusion, and console stay on the paths in the hard-rules table. `packages/realai-core` is not a destination for `realai/`. `packages/console` is not a destination for `console.html`.
4. **No shim deletion as cleanup.** Dest-empty re-exports (`realai/v3_orchestrator.py`, `realai/v3_runtime_bridge.py`, root `plugins/`, root `core/`, `self_builder.py`, and the other "do not put logic here" modules) stay while any launcher or import uses them.
5. **No console rewrite inside a move PR.** Console edits happen in `apps/vscode/webview/console.html` and are copied to root `console.html` in the same commit. A reorg PR does not restyle the console.
6. **No fusion "upgrade" by file size.** The larger `apps/fusion-ui/index.html` does not replace product-root `fusion-ui/`.
7. **No App Builder merge.** Root `src/` and `package.json` name `app-builder-workspace` are not absorbed into `frontend/` or the hive.
8. **No weight files in git.** GGUF and checkpoints stay on `C:\models` / `C:\llama-vulkan\models`.
9. **This PR does not reorganize the filesystem.**

---

## Phase risk summary

| Phase | Touches code? | Risk | Rollback |
|-------|---------------|------|----------|
| 0 contract | no | none | revert the docs PR |
| 1 names | docs / version label only | low | revert |
| 2 park dumps | `git mv` into `_quarantine` | medium (hidden imports, large diff) | `git mv` back |
| 3 one import path | grep, shim, park twins | medium (console/fusion serve paths) | restore shim; hashes must match |
| 4 launchers | bats and root drawer | low–medium (operator scripts) | restore the bat at the old path |
| 5 promote | single files from shelves | high if batched; low per file | revert that file |

---

## Done when

1. A new contributor finds hive, bridge, plugins, organs, fusion, console, and frontend from `docs/MONOREPO_TARGET_LAYOUT.md` in one minute.
2. `import realai.v3_orchestrator` and `import realai.plugins` work from `C:\RealAI-clean`.
3. `:8001/health` and `:8080/health` match the smoke table on the operator machine.
4. `apps/vscode/webview/console.html` and root `console.html` hash-match.
5. `_quarantine/`, recovery branches, and external shelves are still intact and unmerged.
6. No `v1/` or `v2/` directory exists.
