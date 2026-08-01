# agent_tools gap recovery

Generated: `2026-07-14T15:41:05.701597+00:00`

## What was recovered

### Full source (from GitHub clone)
`C:\Users\tsmit\Documents\GitHub\realai\realai-core\agent_tools`

- `__init__.py`, `cli.py`, `dashboard.py`, `executor.py`, `importer.py`, `models.py`, `registry.py`, `runtime.py`

### Staged at
- `recovered/from_agent_tools/agent_tools/` — recovery workspace
- `recovered/from_agent_tools/from_github_realai_core/` — pure github copy
- `realai/agent_tools_gold/` — discoverable under package tree
- `realai-core/agent_tools/` — restored core package path

### Still partial
- `engine/`, `providers/`, `tooling/` — placeholders from SOURCES.txt (not in github core package)
- Historical `.pyc` (Python 3.14) — decompile failed on 3.12 decompyle3; disassembly saved under `disassembly/`

### Hollow path (do not re-merge)
`C:\Users\tsmit\realai\agent-tools\agent-tools-main` — egg-info + locks only

## Self-heal note
Promote queue dry-run: most remaining items already identical or missing_source under deleted backup paths.
Gap recovery is manual curated copies from external gold + github, not bulk promote.
