# Self-heal + gap recovery session

**When:** 2026-07-14  
**Mode:** REALAI_SELF_IMPROVE=true · curated recover · no bulk-merge

## Self-heal loop (ran)

| Step | Result |
|------|--------|
| Learn keywords | **301** keywords (added agent_tools_main, agents) |
| Assemble gold index | OK — promote_queue refreshed (188 items) |
| Promote dry-run | OK — would_copy **0**, already_identical 21, missing_source 33, skipped 136 |
| Full cycle | **ok=true** (assemble → promote dry → ability_learn → evaluate → training plan → verify) |
| Verify matrix | **pass** (rc 0) |
| Ability coverage | **43.6%** weighted (5 LIVE) — honest product score |

Promote cannot fill most remaining queue rows: sources under deleted `backup/clean_backup_*` paths, or already present on authority.

## Gap recovery that *did* land

### agent_tools (major gap)

| Action | Detail |
|--------|--------|
| Problem | `C:\Users\tsmit\realai\agent-tools\agent-tools-main` hollow (locks/egg-info only) |
| Gold found | **GitHub clone** `C:\Users\tsmit\Documents\GitHub\realai\realai-core\agent_tools` — full `.py` |
| Also | Historical `.pyc` (3.14) → decompile failed on 3.12; disassembly + SOURCES scaffold kept |

**Restored modules (real source):**

- `cli.py` (14.6KB), `dashboard.py` (45KB), `runtime.py` (10KB)
- `executor.py`, `importer.py`, `registry.py`, `models.py`, `__init__.py`

**Staged at:**

- `recovered/from_agent_tools/agent_tools/`
- `recovered/from_agent_tools/from_github_realai_core/`
- `realai/agent_tools_gold/`
- `realai-core/agent_tools/` (restored path)

Also: `overmind_runner.py`, `extract_from_agent_tools.py` under recovered.

**Still open:** `engine/`, `providers/`, `tooling/` only as SOURCES placeholders (not in github core package).

### Earlier curated gold (still present)

- Desktop orchestration / hierarchical agent
- Atomic Fizz `plugins/atomic_fizz_realai`
- Frontend `models/route.ts`
- Users memory (already identical)

## External roots

**50/50** present on disk (era_map + ability catalog).

## How to re-run

```bat
set REALAI_SELF_IMPROVE=true
python -m realai.v3_orchestrator --host 127.0.0.1 --port 8001

curl -X POST http://127.0.0.1:8001/v1/self-heal/learn-keywords
curl -X POST http://127.0.0.1:8001/v1/self-heal/cycle -H "Content-Type: application/json" -d "{\"apply\":false}"
```

Offline:

```bat
set REALAI_SELF_IMPROVE=true
python -c "from realai.self_heal import run_full_cycle; print(run_full_cycle(False)['ok'])"
```

## Next recovery priorities

1. Recover `agent_tools/engine|providers|tooling` from git blob history if they exist  
2. Wire `agent_tools_gold` executor into `/v1/tools/execute` (read-only first)  
3. Wire `orchestration_gold` / hierarchical agent as optional multi-agent mode  
4. Only `apply:true` promote when queue shows non-zero `would_copy` of trusted paths  

## Policy reminder

Never bulk-merge OG/backups/node_modules. Curated promote + recovered staging only.
