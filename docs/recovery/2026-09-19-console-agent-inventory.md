# 2026-09-19 — Console agent + recovery inventory

Follow-up to the Grok Bot chat (`Hey – I'm here..txt` / chat id
`b7467e19-f42d-4044-a1a4-184c658e01a5`).

## Console / work-anywhere (shipped this pass)

- Easy-mode system text now injects `HARD_IDENTITY_LOCK` **plus**
  `OPERATOR_SYSTEM` from `docs/CONSOLE_OPERATOR_DIRECTIVE.md`.
- Natural writes auto **re-read** after success (inspect → write → verify).
- Multi-step: repo+write asks inspect first, then one write, then verify.
- Chat workspace switch: `work in C:\path` or a git URL (learn then bind).
- Session workspace persists across Console turns (`session_id` /
  `console-default`).
- `GET /v1/workspace` reports the active root.
- Docs: `scripts/realai-go.ps1` called out in `QUICKSTART_LOCAL.md` and
  `How to run RealAI.txt`.
- Tests: `tests/bot/test_natural_mode.py`, `tests/bot/test_craft_file_ops.py`
  (48 passing).

## Gold / reconstruction names from the chat

| Name | Live status |
|------|-------------|
| `era_map.py` | `scripts/era_map.py` |
| `stack_health.py` | `scripts/stack_health.py` |
| `bench_world_model.py` | `benchmarks/bench_world_model.py` |
| `bench_stack_health.py` | `benchmarks/bench_stack_health.py` |
| `roots_ingest.py` | `scripts/roots_ingest.py` |
| `assemble_gold.py` / `assemble_gold_index.py` | both under `scripts/` |
| `gold_index.py` | `scripts/gold_index.py` |
| `dds3.py` / `dds3_deep_gold_map.py` | both under `scripts/` |
| `verify_matrix.py` / `verify_v3_matrix.py` | both under `scripts/` |
| `ingest_realai_roots.py` | `realai/scanners/ingest_realai_roots.py` |
| `plugin_registry.py` | `realai/plugin_registry.py` (+ plugins copy) |
| `promote_eval.py` | **no body found** (live or quarantine scanners) |
| `ability_matrix.py` | **no body found** (live or quarantine scanners) |

Most chat-era “missing” modules are already present (often as thin aliases
next to the longer canonical names). Remaining reconstruction work is
optional drafts for `promote_eval` / `ability_matrix` only if those
behaviors are still required — do not invent large modules without a
source tree.
