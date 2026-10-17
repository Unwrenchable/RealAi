# Merge ledger: version families (2026-10-16, updated 2026-10-17)

Duplicate modules are merged into one canonical file (union of unique functions and fixes) instead of picking a copy.
Sources were read read-only; nothing was moved or deleted. Machine-readable: `config/merge_ledger.json`.

## Method

inventory 12,745 .py (AST defs per file) + 2,186 branch files; families = same normalized module name + def-name Jaccard >= 0.34 (0.6 for generic names); git-tracked copies of C:\RealAI-clean are ancestors of the branch and excluded; canonical = wired branch member, then AUTHORITY prefix order.

Sources: `C:\RealAI-clean (incl. _quarantine, archive, _parked, recovered, realai\.learn_cache)`; `C:\RealAI-gold`; `C:\RealAI-snapshots`; `C:\Users\tsmit\realai-installer-build\payload\hive`; `C:\Users\tsmit\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS\ai\realai (JS only, no Python versions)`.

## Counts

| | |
|---|---:|
| divergent families | 175 |
| archive only divergent | 4 |
| analyzed | 175 (45 function-level 10-16, 130 priority-9 classified 10-17) |
| merged files | 23 |
| missing defs in analyzed | 9 |
| recovered defs | 5 |
| recovered impl merges | 4 |
| divergent impls in analyzed | 108 |
| conflicts explained by git history | 122 |

## Merged

| canonical | recovered | from | commit |
|---|---|---|---|
| `realai/orchestration/v3_orchestrator.py` | _run_tool: agent_info (read-only agent lookup); _run_tool: read_file/list_dir -> workspace_read/workspace_list; _run_tool: overseer_77 / world-brain aliases | recovered/from_d_roots/realai_archive/_quarantine/v3_orchestrator.py (C:\RealAI-clean, 2026-08-28) | ac7db49 |
| `agents/agent_runtime.py` | MultiAgentPipeline.run: publish each stage on MESSAGE_BUS (guarded); MultiAgentPipeline.run result: message_bus_id | realai/agent_runtime/agent_runtime/agent_runtime.py (single MessageBus hot path phase, 2026-08-23) | c1e67a9 |
| `agent_tools/registry.py` | recommend_profile() | agents/registry.py / realai/plugins/registry.py (2026-08-07); caller realai/agent_tools_gold/cli.py | c1e67a9 |
| `realai/orchestration/v3_runtime_bridge.py` | _PWC_PROMPTS planner/worker: Apache Hive/Hadoop/Hive CLI/Hiveserver2 drift guard | recovered/from_d_roots/realai_archive/_quarantine/v3_runtime_bridge.py | 56935bb |
| `abilities/hive_orchestrator.py` | ABILITY.source -> realai.orchestration.hive_router | realai/hive_orchestrator.py | 56935bb |
| `realai/plugins/rackup_coach/abilities/ledger_audit.py` | ABILITY metadata (read_only, authorize_payout=False) | abilities/rackup/ledger_audit.py | 3a2d7bd |
| `realai/plugins/rackup_coach/abilities/money_anomaly.py` | ABILITY metadata (read_only, authorize_payout=False) | abilities/rackup/money_anomaly.py | 3a2d7bd |
| `realai/plugins/rackup_coach/abilities/payout_sanity.py` | ABILITY metadata (read_only, authorize_payout=False) | abilities/rackup/payout_sanity.py | 3a2d7bd |
| `realai/core/approval_gate.py (new)` | approval gate: request -> human approve -> execute once; dry-run diff/command/plan; workspace scope; protected paths; audit jsonl; money refused | Travis decision 5; replaces the unmerged 2026-08-28 search_replace / shell=True run_terminal_command | 421ba1c |
| `realai/orchestration/v3_orchestrator.py` | _run_tool: search_replace/run_command/run_script/write_file/auto_wire/self_heal promote/self_extend/self_repair -> approval request (REALAI_EXEC_UNGATED escape removed 2026-10-17, 2577edb) | archive phase write/shell tools (restored behind the gate) | 421ba1c |
| `realai/core/tools/hive_executor.py` | _approval_confirm: model-supplied approved=True ignored (REALAI_APPROVAL_TRUST_FLAG=1 to trust); approval must match the tool | security fix | 421ba1c |
| `realai/hive_tools/approvals.py (new)` | request_approval hive tool (request-only, sandbox store offline) + verify contract + spotcheck approval_command / approval_money_refuse | decision 5 self_data rule | 421ba1c |
| `realai/core/self_heal.py (new canonical)` | full union: _probe_routes, run_curated_promote, run_deep_promote, roots ingest, discover modes; promote apply gated; realai/self_heal.py + realai/core/agents/self_heal.py -> alias shims | realai/self_heal.py (1.2-route-probe) + realai/core/agents/self_heal.py (1.1-5F) + 31 archive copies (no extra defs) | 421ba1c |
| `realai/voice_service/ (new) + abilities/voice_service.py` | shared voice client: lab :8890 first, canonical engine fallback, optional :8891 front-end; agent_tools/tts_engine.py -> shim | realai/voice/tts_engine.py already the complete union (the .learn_cache copy is CRLF-identical; agent_tools copy is a subset and was unimportable) | 8f4c5dd |
| `realai/craft.py -> shim of realai/cli/craft.py` | none needed: every realai/craft.py def exists in cli/craft.py (cli adds 23, refines 17) | realai/craft.py (2026-09-24 phase) | cc38c58 |
| `realai/core/local_models.py` | LocalModelManager.get_llm, LocalLLMEngine._load_peft_transformers / _generate_peft_transformers + peft-transformers branches, qwen2.5-1.5b-lora fallback mapping; plugins/local_models.py + plugins/core/local_models.py -> shims | imports/promoted/local_models.py | cc38c58 |
| `realai/core/training/extract_from_agent_tools.py` | sessions_to_instruction_samples, extract_all_training_sources, _read_jsonl, _repo_root (fixes closed_loop import), load_json, normalize_agent_tool_log, agent_tool_log_samples; realai/training copy -> shim | realai/training/extract_from_agent_tools.py + training/extract_from_agent_tools.py | cc38c58 |
| `realai/server/legacy_api.py (new canonical)` | union of api_server phases + POST /v1/memory/recall + opt-in _log_request_row; old api_server paths -> shims; plugins/realai_local_server.py -> shim | realai/api_server.py, core/api_server.py, plugins/api_server.py, plugins/api_big_server.py, RealAI-gold clean_backup_20260708 | 806640f |
| `realai/server/router.py + app.py + legacy_bridge.py` | REALAI_SERVER_MERGED_ROUTES=1 serves legacy-only routes on :8000 (default off); app.py logger fix | decision 1 | 806640f |
| `realai/local_sdxl.py + abilities/image_generation.py` | SDXL-Turbo local images (REALAI_IMAGES_LOCAL_SDXL=1); image_generation local-only (xAI path removed) | origin/feat/local-image-sdxl-turbo 9314a7c (files only) | 806640f |
| `realai/core/approvals_config.py (new)` + approval_store / gate / hive_executor / approval_status | one approvals store (env > config/approvals.json > C:\RealAI-clean\.approvals.json on Windows, temp elsewhere); REALAI_EXEC_UNGATED removed; hive_executor never denies silently | Travis 2026-10-17 items 1, 2, 3, 7 | 2577edb |
| `realai/voice_service/hive.py (new)` + v3_orchestrator voice_* + abilities/audio_speech.py | voice tools and audio_speech routed through realai.voice_service (lab-first) | Travis 2026-10-17 item 4 | b8b0325 |
| `realai/start_realai.bat` + `realai/server/app.py` __main__ | real server entry `python -m realai.server.app --host 127.0.0.1 --port 8000` (no realai_cli serve/doctor) | Travis 2026-10-17 item 6 | 59eb6aa |
| `realai/scripts/train_lora_local.py` | _resume_vulkan_stack, vulkan_runtime pause, --resume-vulkan / --no-resume-vulkan / --resume-gguf | scripts/train_lora_local.py (product-root runner) | bd79200 |
| `realai/scripts/vulkan_runtime.py` | resume_vulkan start via WMI Win32_Process.Create (outlives job object) / POSIX start_new_session | scripts/vulkan_runtime.py | bd79200 |
| `realai/core/training/train_qwen_lora_directml.py` | GRAD_ACCUM (TRAIN_GRADIENT_ACCUMULATION_STEPS, default 1 = unchanged) | RealAI-gold orphans/grok-realai2-clean-2026-07-31 draft | bd79200 |

## Needs Travis's decision

Resolved by Travis's decisions (2026-10-16, 11:46 PM):

- ~~v3_orchestrator write/shell tools~~ -> restored behind the approval gate (docs/APPROVAL_GATE.md), 421ba1c
- ~~xAI image/video/vision paths~~ -> stay out (local only); image_generation now SDXL-Turbo local, 806640f
- ~~Voice tts_engine versions~~ -> realai/voice/tts_engine.py already complete; shared client realai/voice_service (docs/VOICE_SERVICE.md), 8f4c5dd
- ~~Self-heal canonical location~~ -> realai/core/self_heal.py, old paths shims, 421ba1c
- ~~Server twins~~ -> realai/server/legacy_api.py + shims + opt-in bridge (docs/SERVERS.md), 806640f
- ~~realai/craft.py vs realai/cli/craft.py~~ -> cli/craft.py canonical, realai/craft.py shim, cc38c58
- ~~local_models PEFT path~~ -> merged into realai/core/local_models.py, cc38c58

Resolved by Travis's decisions (2026-10-17, 12:21 AM):

- ~~REALAI_EXEC_UNGATED~~ -> removed; console sessions use the gate (2577edb)
- ~~Approval store path~~ -> one store, realai/core/approvals_config.py + config/approvals.json (2577edb)
- ~~craft exemption~~ -> none; craft goes through the gate
- ~~hive_executor silent deny~~ -> files the request (by-path fallback) or returns a clear approval_error (2577edb)
- ~~voice_* / audio_speech~~ -> realai.voice_service (b8b0325)
- ~~merged routes / local SDXL default~~ -> stay off on :8000 (test added, 59eb6aa)
- ~~start_realai.bat realai_cli serve~~ -> python -m realai.server.app (59eb6aa)

Resolved (2026-10-17, 12:41 AM): ~~AGENT_REGISTRY property~~ stays dropped (it was a bug); ~~test_default_model_unchanged~~ clears REALAI_DEFAULT_MODEL itself.

Open:

- realai/core/training/finetune.py plan default data dir (realai/core/datasets/processed) vs RealAI-gold main-realai (<repo>/training/data)
- 326 impl-level conflicts in the 130 priority-9 families (210 in copies with newer mtime, mostly .learn_cache / installer payload copies) were classified, not line-reviewed

## Decision batch families (priority 9, analyzed 2026-10-16 late)

| family | versions | missing defs found | outcome |
|---|---:|---:|---|
| `realai/api_server.py` (incl. core/plugins/big + gold stub) | 31 | 0 in family (+6 in the gold stub; 2 recovered, 4 superseded) + /v1/memory/recall route | realai/server/legacy_api.py |
| `realai/server/router.py` / `app.py` | 23 / 4 | 0 | canonical, opt-in bridge + SDXL |
| `realai/plugins/realai_local_server.py` | 3 | 8 (all in realai/server/realai_local_server.py) | server copy canonical; plugins -> shim |
| `realai/cli/craft.py` | 4 | 0 (22 conflicts = older realai/craft.py phase) | realai/craft.py -> shim |
| `realai/core/local_models.py` | 30 | 3 | recovered (PEFT) |
| `realai/core/training/extract_from_agent_tools.py` | 7 | 6 | recovered (union) |
| `realai/core/agents/agents.py` | 11 | 1 (module-level property bug) | not recovered (open item) |
| `realai/core/training/finetune.py` | 2 | 2 constants (gold data dir) | open item |
| `realai/core/{self_improvement,closed_loop,self_builder,audit,identity,inference/chat_pipeline}.py`, `realai/core/agents/{critic,executor,planner,synthesizer,worker,supervisor}.py`, `realai/core/tools/{code,file,registry,web3}.py`, `realai/plugins/tools/harden_repos.py`, `realai/training/eval.py`, `realai/core/web3/{evm,solana}_backend.py` | 1-12 each | 0 | canonical already complete (conflicts = older phases); web3 untouched (money paths stay locked) |
| `realai/voice/tts_engine.py` | 3 | 0 | canonical complete; agent_tools copy -> shim |
| `realai/self_heal.py` | 31 | 0 | realai/core/self_heal.py |

## Analyzed families (priorities 1-8)

### `abilities/assemble_gold_index.py` (priority 1, 10 other versions)
Versions: branch x3, archive x1, .learn_cache x3, installer-build x3
- `main`: variant is a subset of canonical; canonical kept

### `abilities/audio_speech.py` (priority 1, 4 other versions)
Versions: branch x1, .learn_cache x1, _quarantine x1, realai-gold x1
- `ABILITY`: not merged: voice area (left untouched this pass) -> Travis
- `run`: not merged: voice area (left untouched this pass) -> Travis

### `abilities/auto_wire.py` (priority 1, 4 other versions)
Versions: branch x1, .learn_cache x1, _quarantine x1, realai-gold x1
- `ABILITY_REGISTRY`: canonical kept: variant targets realai/abilities/registry.json (compat shim dir); auto_wire is write-capable (dry_run class)
- `SEARCH_ROOTS`: canonical kept -> Travis: variant also scans apps/, imports/, recovered/ (would widen a write-capable auto-wirer into archive dirs)

### `abilities/business_planning.py` (priority 1, 2 other versions)
Versions: .learn_cache x1, installer-build x1; 2 differing defs match an older git revision of the canonical

### `abilities/code_engineer_cli.py` (priority 1, 2 other versions)
Versions: _parked x1, realai-gold x1
- `run`: canonical kept (auto): variant lacks 37 canonical lines, adds 15; not individually reviewed

### `abilities/game_world.py` (priority 1, 2 other versions)
Versions: .learn_cache x1, _quarantine x1; 2 differing defs match an older git revision of the canonical

### `abilities/hive_orchestrator.py` (priority 1, 7 other versions)
Versions: branch x2, .learn_cache x2, _quarantine x2, installer-build x1
- `run`: reviewed: canonical is the union (realai.orchestration with core.* fallback)
- `ABILITY`: MERGED (56935bb): source points at the gold location

### `abilities/image_analysis.py` (priority 1, 4 other versions)
Versions: branch x1, .learn_cache x1, _quarantine x1, realai-gold x1
- `ABILITY`: not merged: variant calls the xAI API (external key) - local-only policy; canonical kept -> Travis
- `run`: not merged: variant calls the xAI API (external key) - local-only policy; canonical kept -> Travis

### `abilities/image_generation.py` (priority 1, 4 other versions)
Versions: branch x1, .learn_cache x1, _quarantine x1, realai-gold x1
- `ABILITY`: not merged: variant calls the xAI API (external key) - local-only policy; canonical kept -> Travis
- `run`: not merged: variant calls the xAI API (external key) - local-only policy; canonical kept -> Travis

### `abilities/omnibrain.py` (priority 1, 3 other versions)
Versions: .learn_cache x1, _quarantine x1, installer-build x1; 3 differing defs match an older git revision of the canonical

### `abilities/overseer.py` (priority 1, 11 other versions)
Versions: branch x3, .learn_cache x4, _quarantine x1, realai-gold x1, installer-build x2; 2 differing defs match an older git revision of the canonical
- `run`: reviewed: canonical newer (persona prompt + local_chat); variants are thin run_agent wrappers / hardcoded :8001 call

### `abilities/quarantine_reconstruct.py` (priority 1, 2 other versions)
Versions: _parked x1, realai-gold x1

### `abilities/repo_surface.py` (priority 1, 2 other versions)
Versions: _parked x1, realai-gold x1
- `AUTHORITY`: variant is a subset of canonical; canonical kept

### `abilities/secure_tools.py` (priority 1, 3 other versions)
Versions: .learn_cache x1, _quarantine x1, installer-build x1; 3 differing defs match an older git revision of the canonical

### `abilities/therapy_counseling.py` (priority 1, 2 other versions)
Versions: .learn_cache x1, installer-build x1; 2 differing defs match an older git revision of the canonical

### `abilities/translation.py` (priority 1, 2 other versions)
Versions: .learn_cache x1, installer-build x1; 2 differing defs match an older git revision of the canonical

### `abilities/video_generation.py` (priority 1, 4 other versions)
Versions: branch x1, .learn_cache x1, _quarantine x1, realai-gold x1
- `ABILITY`: not merged: variant calls the xAI API (external key) - local-only policy; canonical kept -> Travis
- `run`: not merged: variant calls the xAI API (external key) - local-only policy; canonical kept -> Travis

### `abilities/voice_streaming.py` (priority 1, 6 other versions)
Versions: branch x1, .learn_cache x2, _quarantine x1, realai-gold x1, installer-build x1; 2 differing defs match an older git revision of the canonical
- `ABILITY`: not merged: voice area (left untouched this pass) -> Travis
- `run`: not merged: voice area (left untouched this pass) -> Travis

### `realai/ability_catalog.py` (priority 1, 14 other versions)
Versions: branch x3, .learn_cache x4, _quarantine x2, realai-gold x2, installer-build x3; 15 differing defs match an older git revision of the canonical
- `RUNDOWN_ABILITIES`: reviewed entry-by-entry: only missing id is hominis_enterprise, renamed to hive_governance (alias module abilities/hominis_enterprise.py kept; "hominis" keyword on hive_governance); field sets identical -> canonical kept
- `scan_tools_cli_surface`: canonical kept (auto): variant lacks 35 canonical lines, adds 13; not individually reviewed
- `emit_training_samples`: canonical kept: only differs in the authority path string (C:\RealAI-clean vs old C:\realai)

### `modules/orchestrators/orchestration_worker.py` (priority 2, 6 other versions)
Versions: branch x2, .learn_cache x2, installer-build x2
- missing `_TOOLS_DIR`: not merged: location-specific sys.path constant for realai/plugins/tools copies; canonical has its own sys.path block
- `_REPO_ROOT_DEFAULT`: canonical kept: location-specific path constant

### `realai/core_hive_router.py` (priority 2, 2 other versions)
Versions: .learn_cache x1, installer-build x1; 4 differing defs match an older git revision of the canonical

### `realai/orchestration/hive_router.py` (priority 2, 2 other versions)
Versions: .learn_cache x1, installer-build x1; 2 differing defs match an older git revision of the canonical

### `realai/orchestration/v3_orchestrator.py` (priority 2, 27 other versions)
Versions: branch x4, .learn_cache x5, _quarantine x4, recovered x1, realai-gold x5, _parked x3, installer-build x5; 43 differing defs match an older git revision of the canonical
- missing `OPERATOR_SYSTEM`: not re-added: deliberately removed in git 16830dc (2026-09-19, "operator directive file" replaced the constant)
- missing `_product_root`: not merged: superseded by canonical _product_home()/_PRODUCT_HOME
- missing `_agents_file`: not merged: superseded by canonical REALAI_AGENTS_PATH default (_PRODUCT_HOME/agents/agentx/agents.json)
- missing `Handler._resolved_api_base`: not merged: canonical _fusion_config_js builds api_base inline; gold version depends on realai.server_settings, which does not exist
- `TRAINING_DATA`: canonical kept: location-specific path constant (canonical is product-home aware)
- `AGENTS_PATH`: canonical kept: location-specific path constant
- `MEMORY_DIR`: canonical kept: location-specific path constant
- `_load_agents`: canonical kept (auto): variant lacks 24 canonical lines, adds 3; not individually reviewed
- `_load_agents`: canonical kept (auto): variant lacks 26 canonical lines, adds 6; not individually reviewed
- `_readonly_tools_catalog`: variant is a subset of canonical; canonical kept
- `_run_tool`: reviewed: canonical keeps all tools; read-only names merged; search_replace (file write) and the shell=True run_terminal_command variant NOT merged (canonical has its own gated run_command) -> Travis
- `_enrich_chat_body`: canonical kept (auto): variant lacks 81 canonical lines, adds 3; not individually reviewed
- `_enrich_chat_body`: canonical kept (auto): variant lacks 128 canonical lines, adds 8; not individually reviewed
- `_enrich_chat_body`: canonical kept (auto): variant lacks 74 canonical lines, adds 3; not individually reviewed
- `_enrich_chat_body`: variant is a subset of canonical; canonical kept
- `Handler._cors`: canonical kept (auto): variant lacks 10 canonical lines, adds 2; not individually reviewed
- `Handler._cors`: canonical kept (auto): variant lacks 7 canonical lines, adds 2; not individually reviewed
- `Handler.do_GET`: canonical kept (auto): variant lacks 161 canonical lines, adds 4; not individually reviewed
- `Handler.do_GET`: canonical kept (auto): variant lacks 268 canonical lines, adds 1; not individually reviewed
- `Handler.do_GET`: canonical kept (auto): variant lacks 162 canonical lines, adds 15; not individually reviewed
- `Handler.do_GET`: canonical kept (auto): variant lacks 157 canonical lines, adds 4; not individually reviewed
- `Handler.do_GET`: canonical kept (auto): variant lacks 53 canonical lines, adds 4; not individually reviewed
- `Handler.do_POST`: reviewed: parked 2026-09-07/08 branches (orch2, realai-gateway, xtts-console): canonical already has easy_tools/live_exec/agent_activity/plan_call/maybe_voice_route/publish_dispatch; the XTTS voice-lab proxy variant is voice -> Travis
- `main`: canonical kept (auto): variant lacks 23 canonical lines, adds 2; not individually reviewed
- `main`: canonical kept (auto): variant lacks 38 canonical lines, adds 2; not individually reviewed
- `main`: canonical kept (auto): variant lacks 22 canonical lines, adds 11; not individually reviewed
- `main`: canonical kept (auto): variant lacks 21 canonical lines, adds 2; not individually reviewed
- `DEFAULT_MODEL`: canonical kept: model id default differs by phase; canonical is current
- `_FUSION_UI_DIR`: canonical kept: location-specific path
- `Handler._send_bytes`: variant is a subset of canonical; canonical kept
- `Handler._fusion_config_js`: canonical kept (auto): variant lacks 8 canonical lines, adds 3; not individually reviewed
- `Handler._serve_fusion_ui`: canonical kept (auto): variant lacks 17 canonical lines, adds 8; not individually reviewed

### `realai/orchestration/v3_runtime_bridge.py` (priority 2, 3 other versions)
Versions: .learn_cache x1, _quarantine x1, realai-gold x1; 6 differing defs match an older git revision of the canonical
- `tools_catalog`: variant is a subset of canonical; canonical kept
- `_PWC_PROMPTS`: MERGED (56935bb): union - canonical LANDED/PROPOSED rules kept + variant drift guard added
- `_run_planner_worker_critic`: canonical kept (auto): variant lacks 115 canonical lines, adds 5; not individually reviewed
- `execute_registry_tool`: canonical kept (auto): variant lacks 190 canonical lines, adds 6; not individually reviewed
- `_ROOT`: canonical kept: location-specific path constant
- `_product_root`: canonical kept: location-specific path constant
- `_agents_path`: canonical kept (auto): variant lacks 6 canonical lines, adds 1; not individually reviewed
- `_AGENTS`: canonical kept: location-specific path constant
- `_GITHUB_AGENTS`: canonical kept: location-specific path constant
- `_core_tool_registry`: canonical kept (auto): variant lacks 4 canonical lines, adds 1; not individually reviewed
- `_agent_tools_pkg`: variant is a subset of canonical; canonical kept
- `invoke_agent_tool`: reviewed: canonical newer (defaults to filesystem list instead of erroring)
- `_VulkanChatClient.chat_completion`: variant is a subset of canonical; canonical kept

### `agent_tools/__init__.py` (priority 3, 3 other versions)
Versions: branch x1, .learn_cache x1, installer-build x1
- `__all__`: false family: realai/core/agents/__init__.py is a different package (core agents exports), not a version of agent_tools
- `__getattr__`: false family: different package

### `agent_tools/agents_impl/memory_summarizer_agent.py` (priority 3, 15 other versions)
Versions: branch x5, .learn_cache x5, installer-build x5

### `agent_tools/cli.py` (priority 3, 1 other versions)
Versions: realai-gold x1
- `_build_parser`: canonical kept (auto): variant lacks 6 canonical lines, adds 1; not individually reviewed
- `cmd_run`: canonical kept (auto): variant lacks 46 canonical lines, adds 4; not individually reviewed
- `main`: canonical kept (auto): variant lacks 11 canonical lines, adds 1; not individually reviewed

### `agent_tools/engine/executor.py` (priority 3, 1 other versions)
Versions: realai-gold x1
- `AgentExecutor.run`: reviewed: canonical newer (session-scoped namespaces, history, semantic context)

### `agent_tools/engine/memory.py` (priority 3, 8 other versions)
Versions: branch x2, archive x1, .learn_cache x2, _quarantine x1, installer-build x2
- `RedisMemoryAdapter.append`: canonical kept (auto): variant lacks 5 canonical lines, adds 1; not individually reviewed
- `RedisMemoryAdapter.read`: canonical kept (auto): variant lacks 13 canonical lines, adds 1; not individually reviewed
- `RedisMemoryAdapter.search`: canonical kept (auto): variant lacks 5 canonical lines, adds 1; not individually reviewed

### `agent_tools/filesystem.py` (priority 3, 2 other versions)
Versions: _parked x1, realai-gold x1
- `get_tool_definition`: canonical kept: description wording only
- `_handle_filesystem`: canonical kept (auto): variant lacks 10 canonical lines, adds 3; not individually reviewed

### `agent_tools/overmind_runner.py` (priority 3, 7 other versions)
Versions: branch x2, .learn_cache x2, realai-gold x1, installer-build x2

### `agent_tools/realai.py` (priority 3, 1 other versions)
Versions: realai-gold x1
- `RealAIProvider.complete`: canonical kept (auto): variant lacks 39 canonical lines, adds 5; not individually reviewed

### `agent_tools/registry.py` (priority 3, 11 other versions)
Versions: branch x4, .learn_cache x4, _quarantine x1, installer-build x2
- missing `recommend_profile`: MERGED (c1e67a9)
- `_merge_json_lists`: canonical kept: variant only adds a docstring
- `_load_json_resource`: variant is a subset of canonical; canonical kept
- `assess_agent_access`: canonical kept (auto): variant lacks 4 canonical lines, adds 1; not individually reviewed

### `agent_tools/solana.py` (priority 3, 3 other versions)
Versions: branch x1, .learn_cache x1, installer-build x1

### `agent_tools/tooling/registry.py` (priority 3, 2 other versions)
Versions: _parked x1, realai-gold x1
- `ToolRegistry.auto_wire`: canonical kept (auto): variant lacks 13 canonical lines, adds 1; not individually reviewed
- `ToolRegistry.invoke`: reviewed: canonical newer (adds "*" wildcard)

### `agents/agent_runtime.py` (priority 3, 127 other versions)
Versions: branch x38, .learn_cache x38, _quarantine x5, archive x4, recovered x1, _parked x2, snapshot x1, installer-build x38
- `MultiAgentPipeline.run`: MERGED: MessageBus publish from nested phase (c1e67a9); other variant is an older subset

### `realai/plugins/rackup_coach/__init__.py` (priority 5, 2 other versions)
Versions: .learn_cache x1, installer-build x1; 3 differing defs match an older git revision of the canonical

### `realai/plugins/rackup_coach/abilities/__init__.py` (priority 5, 2 other versions)
Versions: branch x1, .learn_cache x1; 4 differing defs match an older git revision of the canonical

### `realai/plugins/rackup_coach/abilities/ledger_audit.py` (priority 5, 3 other versions)
Versions: branch x1, .learn_cache x1, installer-build x1
- missing `ABILITY`: MERGED (3a2d7bd)
- `run`: not a duplicate implementation: abilities/rackup/* is the product-root ability wrapper (input/context envelope) around this plugin ability; both kept; metadata merged

### `realai/plugins/rackup_coach/abilities/money_anomaly.py` (priority 5, 3 other versions)
Versions: branch x1, .learn_cache x1, installer-build x1
- missing `ABILITY`: MERGED (3a2d7bd)
- `run`: not a duplicate implementation: product-root wrapper layer; both kept; metadata merged

### `realai/plugins/rackup_coach/abilities/payout_sanity.py` (priority 5, 3 other versions)
Versions: branch x1, .learn_cache x1, installer-build x1
- missing `ABILITY`: MERGED (3a2d7bd)
- `run`: not a duplicate implementation: product-root wrapper layer; both kept; metadata merged

### `realai/plugins/rackup_coach/abilities/shot_of_the_day.py` (priority 5, 12 other versions)
Versions: branch x4, .learn_cache x5, installer-build x3; 12 differing defs match an older git revision of the canonical

### `realai/plugins/rackup_coach/coach_agent.py` (priority 5, 10 other versions)
Versions: branch x3, .learn_cache x4, _quarantine x1, installer-build x2; 10 differing defs match an older git revision of the canonical

### `realai/plugins/rackup_coach/organs_bridge.py` (priority 5, 5 other versions)
Versions: branch x2, .learn_cache x2, installer-build x1; 5 differing defs match an older git revision of the canonical

### `realai/self_heal.py` (priority 8, 31 other versions)
Versions: branch x9, .learn_cache x9, _quarantine x5, realai-gold x1, installer-build x7
- `status`: reviewed: canonical newer (variants lack 10-24 lines per function; extras are older docstrings/steps)
- `run_discover`: reviewed: canonical newer (variants lack 10-24 lines per function; extras are older docstrings/steps)
- `run_promote`: reviewed: canonical newer (variants lack 10-24 lines per function; extras are older docstrings/steps)
- `run_full_cycle`: reviewed: canonical newer (variants lack 10-24 lines per function; extras are older docstrings/steps)
- `abilities_manifest`: reviewed: canonical newer (variants lack 10-24 lines per function; extras are older docstrings/steps)

## Priority-9 families classified (2026-10-17)

130 families: 45 recoverable defs, 39 removed in git (not restored), 326 impl conflicts (210 in copies with newer mtime, mostly .learn_cache / installer payload / gold orphans; not line-reviewed). Recovered defs were reviewed one by one; 3 merged (bd79200), the rest are explained below.

| canonical | versions | missing (rec/removed) | conflicts | resolution |
|---|---:|---:|---:|---|
| `realai/scripts/train_lora_local.py` | 3 | 1/0 | 2 | merged: product-root scripts/train_lora_local.py vulkan pause/resume (_resume_vulkan_stack, --resume-vulkan) |
| `realai/core/training/train_qwen_lora_directml.py` | 1 | 2/0 | 9 | merged GRAD_ACCUM (TRAIN_GRADIENT_ACCUMULATION_STEPS, default 1); RUN_SUBDIR already present as run_subdir |
| `realai/coding_agent.py` | 34 | 0/0 | 2 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/api_server.py` | 31 | 0/27 | 0 | resolved earlier: shim of realai/server/legacy_api.py (806640f) |
| `realai/core/local_models.py` | 30 | 0/0 | 16 | resolved earlier: PEFT merge + shims (cc38c58) |
| `realai/plugins/sample_plugin.py` | 26 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/server/router.py` | 23 | 0/0 | 5 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/ui/realai_gui.py` | 22 | 0/0 | 4 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/models/model_catalog.py` | 15 | 0/0 | 5 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/server/orchestration.py` | 15 | 1/0 | 6 | in-memory TaskOrchestrator.__init__ phase superseded by SQLite persistence (.persistence); not merged |
| `realai/tools.py` | 14 | 0/0 | 5 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/server/memory_store.py` | 13 | 3/0 | 4 | in-memory MemoryRecord/MemoryStore phase superseded by SQLite persistence; not merged |
| `_quarantine/twins_20260926/realai__apps/api/main.py` | 12 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `realai/core/agents/supervisor.py` | 12 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `realai/core/agents/agents.py` | 11 | 1/0 | 10 | AGENT_REGISTRY = property(...) stays dropped (Travis decision 2026-10-17: it was a bug) |
| `realai/core/audit.py` | 11 | 0/0 | 2 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/core/tools/code.py` | 11 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `realai/core/tools/file.py` | 11 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `realai/core/tools/registry.py` | 11 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `realai/core/tools/web3.py` | 11 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `_quarantine/twins_20260921/realai__plugins__plugins/plugin___init__.py` | 10 | 15/0 | 8 | canonical is a quarantine twin; .learn_cache realai/__init__ CitationEngine/_automate_email/_estimate_funding_needs not merged (email automation = send path; package __init__ is the slim client export) |
| `_quarantine/twins_20260926/realai__apps/api/routes/chat.py` | 10 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/plugins/atomicfizz_coach/__init__.py` | 10 | 0/0 | 4 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/plugins/atomicfizz_coach/abilities/__init__.py` | 10 | 1/0 | 1 | explicit ABILITY_RUNNERS registry kept; glob _load auto-discovery belongs to learned coaches |
| `realai/plugins/atomicfizz_coach/abilities/health.py` | 10 | 2/0 | 2 | ABILITY_ID/ALIASES metadata from learned coaches; ping alias already registered explicitly |
| `realai/scanners/promote_gold.py` | 10 | 0/0 | 3 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/server/backends.py` | 10 | 0/0 | 5 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/training/eval.py` | 10 | 0/0 | 2 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/core/agents/critic.py` | 9 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `realai/core/agents/executor.py` | 9 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `realai/core/agents/planner.py` | 9 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `realai/core/agents/synthesizer.py` | 9 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `realai/core/agents/worker.py` | 9 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `realai/core/closed_loop.py` | 9 | 0/0 | 4 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/api/index.py` | 8 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/core/self_builder.py` | 8 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `realai/core/self_improvement.py` | 8 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/plugins/effective_engine_main_coach/abilities/agents_bridge.py` | 8 | 0/0 | 2 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/plugins/effective_engine_main_coach/abilities/repo_map.py` | 8 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/sdk/python/realai_client.py` | 8 | 0/0 | 2 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/core/identity.py` | 7 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/core/training/extract_from_agent_tools.py` | 7 | 0/0 | 7 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/core/web3/evm_backend.py` | 7 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `realai/core/web3/solana_backend.py` | 7 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `realai/plugins/tools/harden_repos.py` | 7 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/recovery_registry.py` | 7 | 0/0 | 3 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/router.py` | 7 | 0/0 | 2 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/training/unsloth_train.py` | 7 | 0/0 | 3 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `_quarantine/twins_20260926/realai__modules__desktop_unique/examples_local_ai.py` | 6 | 2/0 | 8 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/cli/craft.py` | 6 | 0/0 | 22 | resolved earlier: canonical, realai/craft.py shim (cc38c58) |
| `realai/cli/realai_cli.py` | 6 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/plugins/device_selector.py` | 6 | 0/0 | 2 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/plugins/tools/rollout_all_repos.py` | 6 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/scripts/realai_full_loop_integrator_auto_fixed.py` | 6 | 0/0 | 2 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/config/amd_inference.py` | 5 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/core/inference/chat_pipeline.py` | 5 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/plugins/effective_engine_main_coach/abilities/node_context.py` | 5 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/plugins/smart_merge_realai.py` | 5 | 0/0 | 4 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/scripts/setup_local_llama.py` | 5 | 0/0 | 4 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/scripts/stack_health.py` | 5 | 1/0 | 2 | _HERE constant only (scanners/ copy); no behaviour lost |
| `realai/server/llama_cli_backend.py` | 5 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/server/server_settings.py` | 5 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/server/tools_runtime.py` | 5 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/voice/tts_engine.py` | 5 | 0/0 | 9 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `_quarantine/twins_20260926/realai__apps/api/routes/audio.py` | 4 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `_quarantine/twins_20260926/realai__apps/api/routes/embeddings.py` | 4 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `_quarantine/twins_20260926/realai__apps/api/routes/health.py` | 4 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `_quarantine/twins_20260926/realai__apps/api/routes/models.py` | 4 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `_quarantine/twins_20260926/realai__apps/api/routes/tasks.py` | 4 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `_quarantine/twins_20260926/realai__apps/api/routes/voice_ws.py` | 4 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `_quarantine/twins_20260926/realai__apps/api/routes/web3.py` | 4 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `realai/mcp_server.py` | 4 | 0/0 | 3 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/plugins/agent-tools-main/sanity_check.py` | 4 | 0/0 | 8 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/server/app.py` | 4 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/server/config.py` | 4 | 0/0 | 6 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `_quarantine/twins_20260924/realai_agents/router.py` | 3 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/engine/__init__.py` | 3 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/plugins/realai_clean_backup_coach/abilities/abilities_bridge.py` | 3 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/plugins/realai_clean_backup_coach/abilities/modules_bridge.py` | 3 | 0/0 | 2 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/plugins/realai_clean_backup_coach/abilities/packages_bridge.py` | 3 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/plugins/realai_clean_backup_coach/abilities/plugins_bridge.py` | 3 | 0/0 | 2 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/plugins/realai_clean_backup_coach/abilities/route_v1_audio_speech.py` | 3 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/plugins/realai_clean_backup_coach/abilities/route_v1_audio_transcriptions.py` | 3 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/plugins/realai_clean_backup_coach/abilities/route_v1_chat_completions.py` | 3 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/plugins/realai_local_server.py` | 3 | 8/8 | 0 | resolved earlier: shim of realai/server/realai_local_server.py (806640f) |
| `realai/scripts/catalog_good_code_roots.py` | 3 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/scripts/find_self_improve_and_lost.py` | 3 | 0/0 | 2 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/scripts/train_to_chat_gguf.py` | 3 | 0/0 | 3 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/scripts/vulkan_runtime.py` | 3 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/server/embeddings_backend.py` | 3 | 0/0 | 3 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `scripts/deep_promote_scan.py` | 3 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `_quarantine/twins_20260921/realai__plugins__plugins/plugin_test_realai.py` | 2 | 0/0 | 2 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/core/training/finetune.py` | 2 | 2/0 | 2 | _DEFAULT_DATA (<repo>/training/data) vs canonical datasets/processed: pending Travis |
| `realai/doctor.py` | 2 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/lambda_embeddings_audio.py` | 2 | 0/0 | 2 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/learn/scaffold.py` | 2 | 0/0 | 6 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/local_media.py` | 2 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/model_assets.py` | 2 | 2/0 | 3 | _REPO_ROOT/_MODELS_ROOT refactored into repo_root()/models_root(); no callers of the old names |
| `realai/plugins/effective_engine_main_coach/abilities/fastify_context.py` | 2 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/scripts/heal_cli.py` | 2 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/training/llama_tools.py` | 2 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/voice/lab_server.py` | 2 | 0/0 | 2 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/workspace.py` | 2 | 0/0 | 2 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/__init__.py` | 1 | 0/0 | 2 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/__main__.py` | 1 | 0/0 | 5 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/_v1_client.py` | 1 | 0/4 | 2 | no recoverable defs; removed-in-git defs not restored; impl conflicts not line-reviewed this pass |
| `realai/agent_activity.py` | 1 | 0/0 | 2 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/aura/reasoning.py` | 1 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/bot/boot.py` | 1 | 0/0 | 2 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/bot/live_exec.py` | 1 | 0/0 | 2 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/bot/natural_mode.py` | 1 | 0/0 | 9 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/bot/talk_easy.py` | 1 | 0/0 | 2 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/core/metrics/metrics.py` | 1 | 0/0 | 2 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/core/security/python_sandbox.py` | 1 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/examples/examples_limitless.py` | 1 | 1/0 | 19 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/learn/pipeline.py` | 1 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/model_registry.py` | 1 | 0/0 | 17 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/plugins/tools/self_extend_tool.py` | 1 | 1/0 | 1 | extend_capability (2026-08-04 gold orphan) not merged: no callers, writes proposal files outside the approval gate; run() is the gated entry |
| `realai/plugins/tools/self_repair_tool.py` | 1 | 1/0 | 1 | repair(mode) (2026-08-04 gold orphan) not merged: no callers; cycle/assemble modes write; run() is the gated entry |
| `realai/scripts/exportable/realai_server.py` | 1 | 1/0 | 1 | _is_enabled helper inlined in canonical; no behaviour lost |
| `realai/server/inference.py` | 1 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/training/self_data/__main__.py` | 1 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/universe/dispatcher.py` | 1 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `realai/universe/doctor.py` | 1 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `realai/universe/hierarchy.py` | 1 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `realai/universe/knowledge_graph.py` | 1 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `realai/universe/mode.py` | 1 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/universe/recipe_engine.py` | 1 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |
| `realai/universe/registry.py` | 1 | 0/0 | 0 | no recoverable defs; versions are subsets |
| `realai/voice/paths.py` | 1 | 0/0 | 1 | no recoverable defs; impl conflicts not line-reviewed this pass |


## 2026-10-17: smoke, full folder pass, git mining

### self_data smoke (14B on :8080, 3 rows/tool, temp approvals store)
| tool | accepted | rejected | reason / fix |
|---|---|---|---|
| memory_stats, agent_pipeline_plan, hive_routes_status, tool_registry_lookup, self_heal_status, executive_goals | 3 each | 0 | none |
| payout_check | 0 → **3 after fix** | 1 → 0 | `payout_check_fact_missing`. Parser and verifier bugs, not the model: extract_questions now collects all decoded arrays; key_facts skips failed-validation calls; wording list widened (f8ecec7) |
| request_approval | 2 | 1 → 0 | `all_tools_failed_but_answer_claims_success`. Verifier bug: the answer honestly reported the refusal, but `_FAIL` lacked "refused". Now passes offline re-verify (f8ecec7) |

Real model mistakes: 0. Travis picks: e950fa0 (AGENT_REGISTRY property bug stays dropped; test_default_model_unchanged clears REALAI_DEFAULT_MODEL).

### Git history (read-only)
- C:\RealAI-clean: 117 refs, 236 commits, 27,205 unreachable blobs (17,099 unique).
- Nested `realai/.learn_cache/realai`: 72 refs, 704 commits, 647 unique.
- Only `git fsck --unreachable --no-reflogs` was used (`--lost-found` writes into .git).
- Dangling Python blobs with defs not in the tree: 6,937, of which 0 mention RealAI (all vendored venv code).
- **Merged:** `BeliefUpdater._normalize_key` (origin/RealAi-unified) into realai/world_model.py. The old extractor's code/memory pair helpers (nested unreachable c6237d4f) went into realai/core/training/extract_from_agent_tools.py as opt-in `extract_code_and_memory_pairs`.
- **Already present under a new name:** hat_routing `_rack_flags` (now `_smoke_flags`), `_vulkan_forward_enabled` (now in cloud_fallback), rackup_coach `_candidate_rating` / `_expected_score` (now inlined).
- **Not merged (reasons in merge_ledger.json → git_mining_20261017.not_merged):** fake ToolRuntime.execute / handle_tool_execute (unsafe), heavy model discovery, the WSGI unified_server, old vLLM/embedding paths, and the old monolith.
- **Needs decision:** handle_provider_route / handle_tool_route would add new :8000 endpoints.

### Build leftovers
See docs/BUILD_LEFTOVERS.md. It covers the nested .git, in-package setup.py/pyproject, 37 egg-info dirs, 13 duplicate npm names / .next standalone package.json, the missing `_parked*` exclude, and 5 module-vs-package shadowings. Two of the shadowings were fixed without moving anything (realai.world_model, realai.engine).

### Per-folder coverage
- **families** = divergent version families with a member in that folder. A family that spans several folders counts in each one.
- **merged** = families with merged code.
- **all files** = PC file count excluding junk dirs.
- Skipped folders are listed but not read.
- The `.git` row is covered by the git-mining section above.
- Every C:\RealAI-clean module name has a branch counterpart: there are 0 off-branch families with ≥2 versions besides `__init__` and logs/_fix.
- 326 impl-level conflicts in priority-9 families were classified, not line-reviewed (still open).

| folder | all files | .py | js/ts | families | merged | functions recovered | needs-decision | note |
|---|---|---|---|---|---|---|---|---|
| `(root files)` | 90 | 5 | 2 | 2 | 1 | 0 | 0 |  |
| `_parked` | 2285 | 1138 | 381 | 14 | 1 | 0 | 0 |  |
| `_quarantine` | 601 | 374 | 33 | 57 | 3 | 0 | 0 |  |
| `.agentx` | 5 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `.git` | — | 0 | 0 | 0 | 0 | 0 | 0 | skipped (junk/live/data) |
| `.github` | 35 | 1 | 0 | 0 | 0 | 0 | 0 |  |
| `.grok` | 95 | 5 | 0 | 0 | 0 | 0 | 0 |  |
| `.hive` | 3 | 3 | 0 | 0 | 0 | 0 | 0 |  |
| `.kilo` | 1 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `.pytest_cache` | — | 0 | 0 | 0 | 0 | 0 | 0 | skipped (junk/live/data) |
| `.tanstack` | 0 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `.venv-xtts` | — | 0 | 0 | 0 | 0 | 0 | 0 | skipped (junk/live/data) |
| `.vercel` | 60 | 0 | 43 | 4 | 0 | 0 | 0 |  |
| `.vscode` | — | 0 | 0 | 0 | 0 | 0 | 0 | skipped (junk/live/data) |
| `abilities` | 98 | 97 | 0 | 25 | 4 | 1 | 0 |  |
| `adapters` | 7 | 7 | 0 | 0 | 0 | 0 | 0 |  |
| `agent_tools` | 71 | 61 | 0 | 13 | 1 | 1 | 0 |  |
| `agents` | 264 | 42 | 8 | 12 | 2 | 2 | 0 |  |
| `agents-ui` | 2 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `apps` | 216 | 50 | 48 | 12 | 0 | 0 | 0 |  |
| `archive` | 61 | 56 | 0 | 5 | 0 | 0 | 0 |  |
| `artifacts` | — | 0 | 0 | 0 | 0 | 0 | 0 | skipped (junk/live/data) |
| `attachments` | — | 0 | 0 | 0 | 0 | 0 | 0 | skipped (junk/live/data) |
| `aura` | 9 | 4 | 0 | 0 | 0 | 0 | 0 |  |
| `autopilot` | 2 | 0 | 2 | 0 | 0 | 0 | 0 |  |
| `benchmarks` | 43 | 43 | 0 | 0 | 0 | 0 | 0 |  |
| `billing` | 1 | 1 | 0 | 0 | 0 | 0 | 0 |  |
| `bin` | 24 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `config` | 7 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `core` | 5 | 5 | 0 | 0 | 0 | 0 | 0 |  |
| `datasets` | 1 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `desktop` | 2 | 2 | 0 | 0 | 0 | 0 | 0 |  |
| `docs` | 139 | 5 | 0 | 0 | 0 | 0 | 0 |  |
| `examples` | 1 | 1 | 0 | 0 | 0 | 0 | 0 |  |
| `frontend` | 45 | 0 | 29 | 11 | 2 | 2 | 1 | realai/apps/frontend newer chat-UI phase (whole-UI merge would change Settings shape/defaults) |
| `fusion-ui` | 4 | 0 | 2 | 1 | 0 | 0 | 0 |  |
| `imports` | 5 | 4 | 0 | 2 | 0 | 0 | 0 |  |
| `logs` | — | 84 | 0 | 0 | 0 | 0 | 0 | skipped (junk/live/data) |
| `marketplace` | 1 | 0 | 1 | 0 | 0 | 0 | 0 |  |
| `memory` | 1 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `migrations` | 1 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `models` | 19 | 1 | 2 | 0 | 0 | 0 | 0 |  |
| `modules` | 145 | 116 | 8 | 11 | 2 | 0 | 0 |  |
| `node_modules` | — | 0 | 0 | 0 | 0 | 0 | 0 | skipped (junk/live/data) |
| `normalized_datasets` | 2 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `notes` | 1 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `orchestrator` | 1 | 0 | 1 | 0 | 0 | 0 | 0 |  |
| `packages` | 113 | 5 | 88 | 6 | 0 | 0 | 0 |  |
| `personas` | 5 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `plugins` | 4 | 3 | 0 | 1 | 0 | 0 | 0 |  |
| `prompts` | 7 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `providers` | 7 | 2 | 3 | 1 | 0 | 0 | 0 |  |
| `public` | 11 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai_training` | 2 | 2 | 0 | 1 | 0 | 0 | 0 |  |
| `realai.egg-info` | — | 0 | 0 | 0 | 0 | 0 | 0 | skipped (junk/live/data) |
| `recovered` | 3685 | 1233 | 517 | 91 | 7 | 0 | 0 |  |
| `registry` | 9 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `repo_tools` | 49 | 17 | 32 | 1 | 0 | 0 | 0 |  |
| `requirements` | 2 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `results` | — | 0 | 0 | 0 | 0 | 0 | 0 | skipped (junk/live/data) |
| `scan_results` | — | 14 | 0 | 0 | 0 | 0 | 0 | skipped (junk/live/data) |
| `scanners` | 46 | 46 | 0 | 1 | 0 | 0 | 0 |  |
| `schema` | 2 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `screenshots` | — | 0 | 0 | 0 | 0 | 0 | 0 | skipped (junk/live/data) |
| `scripts` | 239 | 143 | 25 | 17 | 1 | 0 | 0 |  |
| `sdk` | 3 | 3 | 0 | 1 | 0 | 0 | 0 |  |
| `server` | 4 | 2 | 1 | 0 | 0 | 0 | 0 |  |
| `src` | 78 | 0 | 76 | 13 | 0 | 0 | 0 |  |
| `state` | 1 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `templates` | 2 | 0 | 2 | 0 | 0 | 0 | 0 |  |
| `tests` | 24 | 24 | 0 | 0 | 0 | 0 | 0 |  |
| `tools` | 6 | 1 | 3 | 0 | 0 | 0 | 0 |  |
| `training` | 30 | 5 | 0 | 2 | 0 | 0 | 0 |  |
| `ui` | 3 | 0 | 2 | 1 | 0 | 0 | 0 |  |
| `voice-lab` | — | 0 | 0 | 0 | 0 | 0 | 0 | skipped (junk/live/data) |
| `realai/(files)` | 125 | 75 | 1 | 21 | 2 | 1 | 0 |  |
| `realai/__pycache__` | — | 0 | 0 | 0 | 0 | 0 | 0 | skipped (junk/live/data) |
| `realai/.continue` | 2 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/.github` | 15 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/.hive` | 26 | 26 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/.kilo` | 3 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/.learn_cache` | 3727 | 2085 | 538 | 156 | 11 | 0 | 0 |  |
| `realai/.pytest_cache__dup1` | — | 0 | 0 | 0 | 0 | 0 | 0 | skipped (junk/live/data) |
| `realai/.realai` | 1 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/.vs` | — | 0 | 0 | 0 | 0 | 0 | 0 | skipped (junk/live/data) |
| `realai/abilities` | 3 | 1 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/adapters` | 8 | 7 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/agent_runtime` | 52 | 52 | 0 | 1 | 1 | 0 | 0 |  |
| `realai/agent_tools` | 2 | 1 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/agent_tools_gold` | 27 | 27 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/agent-tools-main` | 2 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/api` | 14 | 14 | 0 | 2 | 0 | 0 | 0 |  |
| `realai/app` | 4 | 1 | 3 | 2 | 0 | 0 | 0 |  |
| `realai/apps` | 12 | 0 | 7 | 3 | 2 | 0 | 1 | realai/apps/frontend newer chat-UI phase (untracked, gitignored) |
| `realai/archive` | 2 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/atomic_fizz` | 4 | 4 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/aura` | 18 | 9 | 0 | 1 | 0 | 0 | 0 |  |
| `realai/aura_pkg` | 2 | 2 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/autopilot` | 2 | 0 | 2 | 0 | 0 | 0 | 0 |  |
| `realai/backend_realai` | 13 | 0 | 13 | 1 | 0 | 0 | 0 |  |
| `realai/benchmarks` | 28 | 28 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/billing` | 1 | 1 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/bin` | 23 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/bot` | 9 | 9 | 0 | 4 | 0 | 0 | 0 |  |
| `realai/catalog` | 12 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/chat` | 1 | 0 | 1 | 1 | 0 | 0 | 0 |  |
| `realai/cli` | 33 | 30 | 0 | 2 | 0 | 0 | 0 |  |
| `realai/commands` | 1 | 0 | 1 | 0 | 0 | 0 | 0 |  |
| `realai/components` | 9 | 0 | 9 | 3 | 0 | 0 | 0 |  |
| `realai/config` | 14 | 6 | 0 | 1 | 0 | 0 | 0 |  |
| `realai/context` | 2 | 1 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/core` | 141 | 139 | 2 | 30 | 2 | 6 | 2 | realai/core/training/finetune.py default data dir |
| `realai/data` | 2 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/datasets` | 9 | 2 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/docs` | 31 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/engine` | 7 | 7 | 0 | 2 | 0 | 0 | 0 |  |
| `realai/examples` | 6 | 6 | 0 | 1 | 0 | 0 | 0 |  |
| `realai/executive` | 12 | 9 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/fusion-ui` | 1 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/inference` | 12 | 12 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/learn` | 11 | 11 | 0 | 2 | 0 | 0 | 0 |  |
| `realai/logs` | — | 0 | 0 | 0 | 0 | 0 | 0 | skipped (junk/live/data) |
| `realai/marketplace` | 1 | 0 | 1 | 0 | 0 | 0 | 0 |  |
| `realai/mcp` | 4 | 2 | 1 | 1 | 0 | 0 | 0 |  |
| `realai/memory` | 121 | 79 | 1 | 4 | 0 | 0 | 0 |  |
| `realai/metrics` | 4 | 4 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/middleware` | 4 | 4 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/models` | 30 | 7 | 2 | 1 | 0 | 0 | 0 |  |
| `realai/modules` | 4 | 1 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/orchestration` | 17 | 15 | 0 | 3 | 2 | 4 | 0 |  |
| `realai/orchestrator` | 1 | 0 | 1 | 0 | 0 | 0 | 0 |  |
| `realai/orchestrators` | 15 | 14 | 0 | 3 | 1 | 0 | 0 |  |
| `realai/Output` | — | 0 | 0 | 0 | 0 | 0 | 0 | skipped (junk/live/data) |
| `realai/packages` | 22 | 3 | 4 | 1 | 0 | 0 | 0 |  |
| `realai/plugins` | 361 | 262 | 50 | 43 | 4 | 3 | 0 |  |
| `realai/profiles` | 1 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/prompts` | 7 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/providers` | 26 | 17 | 4 | 2 | 0 | 0 | 0 |  |
| `realai/python` | 2 | 2 | 0 | 1 | 0 | 0 | 0 |  |
| `realai/realai_agent` | 2 | 1 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/realai_training` | 1 | 1 | 0 | 1 | 0 | 0 | 0 |  |
| `realai/realai-backend` | 1 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/realai-cli` | 1 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/realai-frontend__dup1` | 1 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/registry` | 2 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/results` | — | 0 | 0 | 0 | 0 | 0 | 0 | skipped (junk/live/data) |
| `realai/routes` | 10 | 10 | 0 | 1 | 0 | 0 | 0 |  |
| `realai/runtime` | 3 | 3 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/scan_results` | — | 3 | 0 | 0 | 0 | 0 | 0 | skipped (junk/live/data) |
| `realai/scanners` | 5 | 5 | 0 | 1 | 0 | 0 | 0 |  |
| `realai/schema` | 2 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/schemas` | 7 | 7 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/scripts` | 121 | 102 | 0 | 18 | 1 | 0 | 0 |  |
| `realai/sdk` | 3 | 3 | 0 | 1 | 0 | 0 | 0 |  |
| `realai/sdk-py` | 2 | 1 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/sdk-ts` | 2 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/security` | 4 | 4 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/server` | 29 | 27 | 0 | 12 | 0 | 0 | 1 | RealAi-unified router handle_provider_route/handle_tool_route (would add new :8000 endpoints) |
| `realai/skills` | 6 | 6 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/static` | 1 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/templates` | 3 | 1 | 2 | 0 | 0 | 0 | 0 |  |
| `realai/tests` | 26 | 26 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/tooling` | 6 | 6 | 0 | 1 | 0 | 0 | 0 |  |
| `realai/tools` | 19 | 19 | 0 | 3 | 0 | 0 | 0 |  |
| `realai/tools_realai` | 1 | 0 | 1 | 0 | 0 | 0 | 0 |  |
| `realai/tracing` | 2 | 2 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/training` | 30 | 25 | 0 | 5 | 0 | 0 | 0 |  |
| `realai/ui` | 5 | 1 | 2 | 2 | 0 | 0 | 0 |  |
| `realai/universe` | 16 | 15 | 0 | 7 | 0 | 0 | 0 |  |
| `realai/utilities` | 6 | 4 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/voice` | 274 | 19 | 114 | 19 | 0 | 0 | 0 |  |
| `realai/web3` | 6 | 6 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/widget` | 1 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/workflows` | 2 | 0 | 0 | 0 | 0 | 0 | 0 |  |
| `realai/world_model` | 30 | 27 | 0 | 0 | 0 | 0 | 0 |  |

### Fix found by the PC test run (2026-10-17)
`tests/test_cloud_fallback.py::test_chat_completion_clear_cloud_error_without_keys` failed on the PC only, because the 14B on :8080 was up. With `RENDER=true`, `RealAI.chat_completion` still fell through to the `REALAI_LOCAL_HTTP_FALLBACK` path and answered from loopback `:8080`. That bypassed the documented "hosted cloud is an unconditional deny" rule, which predates this branch (introduced in c1186ae). The local-HTTP fallback is now skipped when `is_hosted_cloud()` is true. Local :8000 behaviour is unchanged. Regression test: `test_hosted_cloud_skips_local_http_fallback`.


### Decisions 2026-10-17 (Travis GO, ~02:12 PT)
1. Chat UI: helper only (e029b01); no full merge of realai/apps/frontend.
2. `/v1/providers/route` and `/v1/tools/route` added read-only behind `REALAI_ROUTING_ROUTES=1` (default off; 6676333). No execution path.
3. Build leftovers: branch fixes in cb8e9a1. Archive at `D:\ARCHIVE\build-leftovers-20261017` (MOVE_LOG.md/json): 36 `recovered/**/*.egg-info` moved (472 KB, SHA256-verified); nested `.learn_cache/realai/.git` bundled and verified but **kept** (the learn pipeline would rmtree the cache without it); root `realai.egg-info` **kept** (the realai-train venv resolves the realai-server/realai-craft entry points from it via user PYTHONPATH). Details in docs/BUILD_LEFTOVERS.md.
4. finetune.py keeps its current default data dir.
