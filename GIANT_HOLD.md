# Giant hold (not deleted)

Large trees/files were **moved out** of this git tree so the branch can push to GitHub.
Nothing listed here was deleted.

## Location

`C:\realai_giant_hold\local-recovery-primary-clean-20260731\`

See `MOVED_MANIFEST.txt` in that folder for the full list.

## What moved

| Path | Why |
|------|-----|
| `phase4_tools/plan_phase4_preview/` | ~9.5k generated dry-run previews (multi-GB) |
| `manifests/realai_alt_cavity_manifest.json` | ~2.8 GB scan artifact |
| `manifests/realai_full_cavity_manifest.json` | ~385 MB scan artifact |
| `realai_local_export.zip` | ~1 GB export archive |
| `recovered/.../ASSEMBLED_realai-core.tar.gz` | ~4.8 GB (over GitHub LFS 2 GB limit) |
| `recovered/.../realai-core.tar.gz.part-aa/ab/ac` | split archive parts (~2 GB each) |

## Still in repo

- Unique source/modules under `realai/`, `core/`, `apps/`, `agents/`, `scanners/`, etc.
- `archive/` and other recovered unique code trees
- Smaller cavity manifests and Phase-4 tooling (`phase4_tools/dry_run_scaffold.py`)
- Pointers/maps under recovered (README/RESTORE_MAP)

Restore: copy paths back from the hold into `C:\realai` if needed for local work.
