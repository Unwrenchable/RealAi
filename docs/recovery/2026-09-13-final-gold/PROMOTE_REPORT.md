# Promote dest_empty_promotable + unlink archive junctions

- Generated: 2026-09-13 08:58:16 PT (2026-09-13 15:58:16 UTC)
- Manifest: `C:\RealAI-clean\docs\recovery\2026-09-13-final-gold\dest_empty_promotable.jsonl`
- Gold shelf: `C:\RealAI-gold`
- Live root: `C:\RealAI-clean`
- Log: `C:\RealAI-clean\docs\recovery\2026-09-13-final-gold\promote_log.jsonl`

## Promote results

- **promoted:** 1760 files, **505474950** bytes
- **missing_gold:** 0
- **blocked (total):** 0
- **size_mismatch_after_copy:** 0

### Skipped by reason

- `skipped_live_nonempty`: 21

### Blocked by reason

- (none)

Rules applied: copy only when gold file exists and live path is missing or size 0;
never overwrite non-empty live files; skip unsafe rels (absolute, `..`, outside live root,
or into `_quarantine` / `imports` / `recovered` junction targets). Parent dirs created as needed.

## Junction unlink

Method: `cmd /c rmdir <junction>` (removes the link only). Never `rd /s`, never `Remove-Item -Recurse`.
Placeholders: empty directories with `README.txt` pointing at `D:\RealAI-archive\...` and `C:\RealAI-gold\`.

### `_quarantine`

- link: `C:\RealAI-clean\_quarantine`
- expected target: `D:\RealAI-archive\_quarantine`
- was reparse/junction before: True
- rmdir returncode: 0
- removed: True
- placeholder created: True
- after is ordinary dir (not reparse): True
- after is reparse: False
- target exists after: True

### `imports`

- link: `C:\RealAI-clean\imports`
- expected target: `D:\RealAI-archive\imports`
- was reparse/junction before: True
- rmdir returncode: 0
- removed: True
- placeholder created: True
- after is ordinary dir (not reparse): True
- after is reparse: False
- target exists after: True

### `recovered`

- link: `C:\RealAI-clean\recovered`
- expected target: `D:\RealAI-archive\recovered`
- was reparse/junction before: True
- rmdir returncode: 0
- removed: True
- placeholder created: True
- after is ordinary dir (not reparse): True
- after is reparse: False
- target exists after: True

## D: archive still present

### Before unlink

- `D:\RealAI-archive\_quarantine` exists=True top_entries=347 sampled_files=507 sampled_bytes=262666148
- `D:\RealAI-archive\imports` exists=True top_entries=1 sampled_files=399 sampled_bytes=2720044
- `D:\RealAI-archive\recovered` exists=True top_entries=45 sampled_files=501 sampled_bytes=120142517

### After unlink

- `D:\RealAI-archive\_quarantine` exists=True top_entries=347 sampled_files=507 sampled_bytes=262666148
- `D:\RealAI-archive\imports` exists=True top_entries=1 sampled_files=399 sampled_bytes=2720044
- `D:\RealAI-archive\recovered` exists=True top_entries=45 sampled_files=501 sampled_bytes=120142517

## dir /AL C:\RealAI-clean (after)

```
 Volume in drive C has no label.
 Volume Serial Number is 089F-CC78

 Directory of C:\RealAI-clean

File Not Found
```

