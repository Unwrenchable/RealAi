# Wiring pass 2026-09-21

Goal: v1/v2 modules reachable from live names without breaking existing shims.

## What was broken

| Caller | Asked for | Reality |
|--------|-----------|--------|
| `realai/hive_orchestrator.py` | `core.orchestration.hive_router` | No product-root `core/` package |
| `realai.plugins.rackup_coach` | `plugins.rackup_coach.*` | Only works after root `plugins/` alias loads |
| `realai.plugins` | `sample_plugin` only | RackUp / Atomic Fizz were invisible |
| `realai/plugins/registry.json` | atomic_fizz only | RackUp missing |

Gold was already present:

- `realai/orchestration/v3_orchestrator.py` (153 KB)
- `realai/orchestration/v3_runtime_bridge.py` (81 KB)
- `realai/orchestration/hive_router.py`
- `realai/plugins/rackup_coach/`
- `realai/core/self_*.py`

## What this pass did

1. Added product-root `core/` as **compat shims** to `realai.core` / `realai.orchestration`.
2. Pointed `realai/hive_orchestrator.py` at `realai.orchestration.hive_router`.
3. Switched RackUp plugin to **relative imports** (`.coach_agent`, `.types`).
4. Made `realai.plugins` a real host: `list_first_party`, `load_first_party`, `register_all`.
5. Registered RackUp + Atomic Fizz + sample in `registry.json`.
6. Included `core*` in the installable package set.

## Shims that stay on purpose

Package-root dest-empty modules (`realai/v3_orchestrator.py`, `realai/self_builder.py`, …) re-export gold. Do not put logic in them. Do not delete them until every launcher is grepped.

## Not moved in this pass

- 421 KB `realai/__init__.py` v1 SDK dump — `from realai import RealAI` still depends on it.
- Nested dumps (`realai/realai_repo`, `deep_nests`) — park in a later `git mv` on HOMEPC.
- Recovery-branch desktop gold — promote file-by-file after this wiring lands.
