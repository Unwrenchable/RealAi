# Reorg phases — live stays runnable the whole time

Never merge `recovery/*` or `main` onto live. Each phase is one PR into `live/realai-clean-20260911`.

## Phase 0 — contract (this branch)

- [x] `ARCHITECTURE.md`
- [x] `docs/AUTHORITY.md`
- [x] `docs/LINEAGE.md`
- [x] `docs/TARGET_LAYOUT.md`
- [ ] Point README "Repo layout" at `ARCHITECTURE.md`
- [ ] Stamp `docs/architecture.md` as historical

## Phase 1 — names and front door (no behavior change)

- Bump `pyproject.toml` version to `3.0.0`.
- Move root `AGENTS.md` → `docs/foreign/GROK_APP_BUILDER_AGENTS.md`.
- Add `docs/AGENTS_REALAI.md` (hive / abilities / plugins contract).
- README layout section = target tree only.
- Catalog: any row whose only gold is `C:\\tools\\realai` becomes `PARTIAL`.

## Phase 2 — park nested dumps

Use git mv onto `_quarantine/twins_20260921/`:

- Nested repos inside `realai/` (`realai_repo`, `grok_export_realai`, `deep_nests`).
- Twin plugin trees (`realai/plugins/plugins`, `C_realai_plugins`).
- Root orphan UI files (`layout.tsx`, `globals.css`).

Verify: `python -m realai.v3_orchestrator --help` and `python -c "from realai.ability_catalog import coverage_summary; print(coverage_summary())"`.

## Phase 3 — one import path per module

Grep then delete the loser:

- `abilities/` vs `realai/abilities/` vs `realai/plugins/abilities/`
- `agents/` vs `realai/agents/`
- `modules/organs` vs `realai/modules/organs`

Keep the path Hive already imports. Leave a 10-line shim if something external still imports the loser.

## Phase 4 — promote leftover v1/v2 gold

File-by-file from:

- `recovery/unique-modules/.../gold/`
- `recovery/desktop-orchestration` + `desktop-design-system` + `desktop-unique-py`
- `recovery/plugin-system`
- `recovery/users-tsmit-realai` (only if live file is smaller / stubber)

Tool: `scanners/promote_gold.py`. Accept a file only if it beats live gold on size **and** unique symbols.

## Phase 5 — operator tidy

- Collapse launchers: `START_HERE.bat` + `scripts/windows/`.
- Keep `scanners/` but out of the default mental map (docs index: Runtime vs Tools vs Archive).
- Ignore `_quarantine/`, `recovered/`, `imports/` in pytest (already partly done).

## Done when

1. A new contributor can find hive, plugins, organs, frontend, vscode from README in under a minute.
2. `import realai.v3_orchestrator` and `import realai.plugins.rackup_coach` work from product home.
3. No `v1/` or `v2/` directory exists.
4. Recovery branches still exist, untouched.
