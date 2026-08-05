# P0 filename + aura path hunt (2026-07-16)

## Explicit aura paths (all OK)

| Path | Files |
|------|-------|
| `C:\\Users\\tsmit\\realai_historical_backups\\realai_versions_20260612\\realai_repo\\aura` | main.py, memory.py, reasoning.py, skills/* |
| `C:\\Users\\tsmit\\backups\\realai-sync-20260508-090605\\realai-main\\aura` | same layout |
| `C:\\Users\\tsmit\\Documents\\GitHub\\realai\\aura` | same layout |
| `C:\\Users\\tsmit\\realai_historical_backups\\...\\RealAIProject\\aura` | same layout |

**18 aura/ directories** found under Users\\tsmit total.

## Exact missing filenames under full Users\\tsmit walk

| File | Found? |
|------|--------|
| aura_memory.py | **NO** (gold is `aura/memory.py`) |
| self_extend_tool.py | **NO** |
| self_repair_tool.py | **NO** |
| system_scan_tool.py | **NO** |
| device_selector.py | **YES** — `realai2/plugins/tools/device_selector.py` |
| mcp_server.py | **NO** |
| world_model.json | **NO** (have `world_model.py` many copies) |
| find_realai_bootstrap.py | **NO** |

## Gold extracted / wired

| Artifact | Action |
|----------|--------|
| `aura/memory.py` LongTermMemory + WorkingMemory | Staged + live `aura/` refreshed |
| `realai/aura_memory.py` | **Created** facade `AuraMemory` |
| `device_selector.py` | Staged + live `realai/plugins/tools/` |
| `self_extend_tool.py` | Adapter → self_improvement + proposal staging |
| `self_repair_tool.py` | Adapter → self_heal status/assemble/desktop discover |
| `system_scan_tool.py` | Adapter → recovery/desktop/abilities scans |
| Orchestrator tools | Wired: aura_memory, self_extend, self_repair, system_scan, device_selector |

## Stage dirs

- `recovered/from_aura_p0_hunt/`
- `scan_results/p0_exact_filename_hunt.json`

## Honest conclusion

The four named `*_tool.py` files and `aura_memory.py` / `world_model.json` / `mcp_server.py` / `find_realai_bootstrap.py` **do not exist as those basenames** anywhere under `C:\\Users\\tsmit` (35k+ dirs walked). Closest gold:

- **Aura** package (`memory.py` ≈ aura_memory)
- **world_model.py** (code, not JSON)
- **device_selector.py** (real file recovered)
- **self_heal / self_improvement** (repair/extend behavior)

Adapters now satisfy the missing-filename contracts without inventing fake historical code.
