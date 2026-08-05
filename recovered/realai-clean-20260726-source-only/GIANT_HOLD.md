# Giant hold (not deleted)

Large archive files were **moved out** of this git tree so the branch can push to GitHub.
Nothing listed here was deleted.

## Location

`C:\realai_giant_hold\realai-clean-20260726-source-only\`

See `MOVED_MANIFEST.txt` in that folder for the full list.

## What moved

| Path | Why |
|------|-----|
| `realai-core.tar.gz` | multi-GB core archive |
| `realai-core.tar.gz.part-aa/ab/ac` | split archive parts (~2 GB) |
| `.backup/.../realai-core.tar.gz` | multi-GB backup copy of same archive class |

## Still in repo

- Unique source/modules (`realai/`, `core/`, `apps/`, `archive/`, etc.)
- `.backup/` trees **except** the giant tar.gz above
- `repo_tree*.txt` and other non-giant artifacts

Restore: copy paths back from the hold into `C:\Users\tsmit\realai-clean` if needed.
