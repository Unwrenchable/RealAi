# Restored from Recycle Bin — clear names

Generated: `2026-07-15T14:43:38.804509+00:00`

## Why names looked confusing

In Recycle Bin, Windows renames deleted files to:

- `$I....` = metadata (original path)
- `$R....` = the actual file

Those **$R** names are useless by themselves. This folder restores copies using **original paths/names**.

## Where things are

Root of this restore:

`/mnt/c/realai/recovered/from_recycle_bin/restored_clear_names`

### Important finds
- Model configs: search for `models.yaml`, `registry.json.txt`
- Code shims: `api_server.py`, `config.py`
- Large archive: look for `realai-core.tar.gz.part-aa/ab/ac` and `ASSEMBLED_realai-core.tar.gz` if assembled
- Deleted folders: `*.DIR_NOTE.json` explain how to fully Restore in Explorer

### Stats
- Restored files: **30**
- Restored bytes: **5,016,227,255**
- Dir notes: **12**
- Missing payload (metadata only): **10**
- Secrets skipped: **3**
- Errors: **0**

## Do NOT open secrets into git

Secrets found in Recycle Bin were **not** restored here. Handle wallet/env files outside the repo.

## Full inventory

See `RESTORE_MAP.json` in this folder and `scan_results/recycle_bin_gold_map.json`.
