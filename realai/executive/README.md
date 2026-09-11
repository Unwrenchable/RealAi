# RealAI Executive Loop

Persistent goals with world-state verification. Not chat.

## First slice: Repo Health Watcher

- Goal type: `repo_health`
- Evidence: required package files exist (shims, hive app, universe, craft)
- Human gate: force-push / delete only
- Audit trail: `realai/executive/state/goals.jsonl`

## Watchers (registered)

| Module | Goal type | Mode |
|--------|-----------|------|
| `watchers/repo_health.py` | `repo_health` | file-surface bootability |
| `watchers/rackup_health.py` | `rackup_health` | scaffold: file/env markers only |
| `watchers/caps_watch.py` | `caps_watch` | scaffold: file/env markers only |

Scaffold env markers (optional): `REALAI_RACKUP_MARK`, `REALAI_CAPS_MARK`.

## Act → sense → judge

1. Act: inventory required paths / markers
2. Sense: file/dir exists + sizes (or env mark)
3. Judge: verified | retry | failed | blocked_human

## Daemon entry (user runs later — do not auto-start)

Static CLI entry: `realai/executive/daemon.py` (safe on import; no side effects).

```text
# one cycle then exit
python -m realai.executive.daemon --once

# persistent loop (interval from env, default 3600s)
set REALAI_EXEC_INTERVAL_S=3600
python -m realai.executive.daemon

# optional workspace override
python -m realai.executive.daemon --once --workspace C:\RealAI-clean
```

Flags:
- `--once` — single cycle (load goals → tick open goals → write status) then exit
- `--workspace PATH` — override `REALAI_WORKSPACE` / default `C:\RealAI-clean`

Status snapshot: `realai/executive/state/executive_status.json`

## Voice

Ask "what did you do last night?" → `spoken_status()` returns one clean spoken line for Voice Lab / XTTS (Travis speaker WAV).

## Not in this slice

- No auto daemon start from reconstruction
- No heal / force-push
- No live training
- No network from watchers