# Wiring + surface (live as of 2026-09-21)

Merged to `live/realai-clean-20260911`:

- PR #127 — product-root `core/` shims, `realai.plugins` host, RackUp alias, pyproject 3.0.0
- PR #126 — `ARCHITECTURE.md` contract

This pass adds:

- `realai/hive.py` — public hive surface (status, tools, plugins, catalog)
- `scripts/park_nested_dumps.ps1` — HOMEPC `git mv` of nested dumps into `_quarantine`

## Do not replace yet

`realai/__init__.py` (421 KB) is the v1 `RealAI` / `RealAIClient` SDK.
`from realai import RealAI` still loads it. New code should use `realai.hive`.

## HOMEPC after pull

```powershell
cd C:\RealAI-clean
git checkout live/realai-clean-20260911
git pull
python -c "from realai.hive import hive_status, register_plugins; print(hive_status().get('ok')); print(register_plugins())"
python -m realai.v3_orchestrator --help
# optional park:
powershell -File .\scripts\park_nested_dumps.ps1
```
