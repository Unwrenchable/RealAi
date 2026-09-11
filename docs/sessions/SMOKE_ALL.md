# Smoke — all abilities / tools / agents

Generated: `2026-09-02T11:18:07.146789+00:00`  
Hive: `http://127.0.0.1:8001`  elapsed **33.8s**

## Summary

| Surface | Pass | Fail | Skipped |
|---------|-----:|-----:|--------:|
| Abilities | 59 | 3 | — |
| Tools | 38 | 12 | 66 |
| Agents (GET) | 234 | 0 | — |
| Agent runs (spot) | 4 | 0 | — |

Coverage honesty: **100.0%**

## Failed abilities

- `sotd_contribute` — invalid_shot
- `code_engineer_cli` — ModuleNotFoundError:No module named 'agent_tools.agents_impl.code_engineer_agent'
- `quarantine_reconstruct` — no_run_entrypoint

## Failed tools

- `voice_speak` — empty_speech_text
- `voice_listen` — 
- `craft_run` — unknown_craft_action:status
- `hive_run` — cannot import name 'list_nest_orchestrators' from 'core.orchestration.hive_router' (C:\RealAI-clean\realai\core\orchestration\hive_router.py)
- `overseer` — text_required
- `execute_code` — code required
- `web_research` — query required
- `run_terminal_command` — empty command
- `agent_tools_assess` — unknown_agent:
- `agent_tools_list_tools` — No module named 'agent_tools.tooling.registry'
- `agent_tools_invoke` — No module named 'agent_tools.tooling.registry'
- `core.file_tool` — Permission denied: filesystem

Full JSON: `C:\RealAI-clean\scan_results\SMOKE_ALL_ABILITIES_TOOLS_AGENTS.json`
