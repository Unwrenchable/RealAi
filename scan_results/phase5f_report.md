# Phase 5F — Ability Graph + Keyword Learning + External Gold Roots

## Goal

Make RealAI know the **technical rundown** ability surface, register **all machine RealAI gold roots**, learn keywords for deeper scans, and feed that into self-heal / self-improve.

## What shipped

| Artifact | Role |
|----------|------|
| `scan_results/era_map.json` | All external gold roots registered |
| `realai/ability_catalog.py` | Catalog + learn + training samples |
| `scan_results/ability_catalog.json` | Honest LIVE/PARTIAL/CODE/GOLD/MISSING map |
| `scan_results/ability_keywords_learned.json` | Growing keyword set for DDS-3 |
| `training/data/ability_surface.jsonl` | Self-improve training about own abilities |
| `docs/ABILITY_SURFACE.md` | Human coverage report |
| `realai/self_heal.py` | learn-keywords, coverage in status/cycle |
| `scanners/dds3_missing_files.py` | Learned patterns + external roots |
| `realai/v3_orchestrator.py` | `/v1/capabilities` + `POST .../learn-keywords` |
| `realai/self_improvement.py` | Evaluate attaches ability coverage + emits samples |

## External roots (all registered)

- `C:\tools\realai` — CLI commands/plugins surface
- `C:\Users\tsmit\realai` + `realai-clean`
- `C:\Users\tsmit\realai_historical_backups`
- `C:\Users\tsmit\backups\realai-sync-20260508-090605`
- `C:\Users\tsmit\.realai` + `.agentx` (runtime state)
- Atomic Fizz trees + `C:\Unwrenchable`
- Downloads zips / finetune jsonl / `C:\temp\realai_ui.html`
- Inference siblings: llama-vulkan, llama, models

**Policy:** catalog + keyword learn + curated promote only. **Never bulk-merge.**

## First catalog run

- Coverage vs technical rundown: **~43.6%** weighted (5 LIVE)
- External roots present: **25/25**
- Learned keywords: **282** (first cycle)
- Training samples: **31** → `ability_surface.jsonl`
- CLI surface: chat, help, image, research, system, video, web3 + plugins overseer, render, solana, trading

## How to use

```bat
REM refresh catalog + keywords (needs REALAI_SELF_IMPROVE=true on orch)
curl -X POST http://127.0.0.1:8001/v1/self-heal/learn-keywords

REM deeper ability inventory across authority + external roots
curl -X POST http://127.0.0.1:8001/v1/self-heal/discover -d "{\"mode\":\"abilities\"}"

REM honesty coverage
curl http://127.0.0.1:8001/v1/capabilities
```

Or offline:

```bat
python -m realai.ability_catalog --all
```

## Note

`verify_v3_matrix` pass counts still mean **stack health**, not full product completeness. Use `weighted_pct` from `/v1/capabilities` for rundown closeness.
