# Phase 4 Verify Matrix

Generated: `2026-07-16T17:59:25.574132+00:00`
**31/32 passed** — SOME FAILED

- UI: `http://127.0.0.1:3000`
- Orchestrator: `http://127.0.0.1:8001`
- Vulkan: `http://127.0.0.1:8080`

| Check | Result | Detail |
|-------|--------|--------|
| `vulkan_health` | PASS | {"status": "ok"} |
| `orchestrator_health` | PASS | {"status": "ok", "service": "realai-v3-orchestrator", "vulkan": {"ok": true, "ba |
| `ui_http` | FAIL | {"status": 0} |
| `orch_chat` | PASS | Matrix OK |
| `training_status` | PASS | {"files": 4} |
| `self_improve_status` | PASS | {"enabled": true, "env": "REALAI_SELF_IMPROVE", "modules": {"TrainingDataGenerat |
| `self_heal_status` | PASS | {"scan_messy_repo": true, "assemble_gold": true, "promote_gold": true, "training |
| `self_heal_abilities` | PASS | RealAI Self-Heal |
| `capabilities_catalog` | PASS | {"weighted_pct": 46.0, "ability_count": 31, "external_roots_exist": 60} |
| `tools_catalog` | PASS | {"n": 10} |
| `agent_tools_status` | PASS | {"agents_count": 68, "packages": 3} |
| `tools_agent_tools_list` | PASS | 3 |
| `models_realai_facade` | PASS | {"ids": ["realai-default-coder", "realai-1.0-instruct", "local-llama-3b", "local |
| `agents_list` | PASS | {"count": 68} |
| `tools_list_agents` | PASS | {"tool": "list_agents", "result": {"count": 68, "agents": [{"id": "agent-tools-d |
| `chat_with_agent_memory` | PASS | {"meta": {"orchestrator": "v3", "provider": "realai", "vulkan_base": "http://127 |
| `self_improve_evaluate` | PASS | {"ok": true, "scores": {"ability_coverage_pct": 0.46, "ability_live_count": 7.0, |
| `artifact:scan_results/era_map.json` | PASS | scan_results/era_map.json |
| `artifact:scan_results/gold_index.json` | PASS | scan_results/gold_index.json |
| `artifact:scan_results/promote_queue.json` | PASS | scan_results/promote_queue.json |
| `artifact:scan_results/ability_catalog.json` | PASS | scan_results/ability_catalog.json |
| `artifact:scan_results/ability_keywords_learned.json` | PASS | scan_results/ability_keywords_learned.json |
| `artifact:training/data/realai_finetune_dataset.jsonl` | PASS | training/data/realai_finetune_dataset.jsonl |
| `artifact:training/data/ability_surface.jsonl` | PASS | training/data/ability_surface.jsonl |
| `artifact:realai/self_heal.py` | PASS | realai/self_heal.py |
| `artifact:realai/self_improvement.py` | PASS | realai/self_improvement.py |
| `artifact:realai/ability_catalog.py` | PASS | realai/ability_catalog.py |
| `artifact:realai/v3_orchestrator.py` | PASS | realai/v3_orchestrator.py |
| `artifact:docs/ABILITY_SURFACE.md` | PASS | docs/ABILITY_SURFACE.md |
| `artifact:scanners/assemble_gold_index.py` | PASS | scanners/assemble_gold_index.py |
| `artifact:scanners/promote_gold.py` | PASS | scanners/promote_gold.py |
| `artifact:scanners/dds3_missing_files.py` | PASS | scanners/dds3_missing_files.py |
