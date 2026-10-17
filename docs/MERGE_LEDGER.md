# Merge ledger: version families (2026-10-16)

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
| analyzed | 45 |
| merged files | 8 |
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
| `realai/orchestration/v3_orchestrator.py` | _run_tool: search_replace/run_command/run_script/write_file/auto_wire/self_heal promote/self_extend/self_repair -> approval request (REALAI_EXEC_UNGATED=1 escape, default off) | archive phase write/shell tools (restored behind the gate) | 421ba1c |
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

## Needs Travis's decision

Resolved by Travis's decisions (2026-10-16, 11:46 PM):

- ~~v3_orchestrator write/shell tools~~ -> restored behind the approval gate (docs/APPROVAL_GATE.md), 421ba1c
- ~~xAI image/video/vision paths~~ -> stay out (local only); image_generation now SDXL-Turbo local, 806640f
- ~~Voice tts_engine versions~~ -> realai/voice/tts_engine.py already complete; shared client realai/voice_service (docs/VOICE_SERVICE.md), 8f4c5dd
- ~~Self-heal canonical location~~ -> realai/core/self_heal.py, old paths shims, 421ba1c
- ~~Server twins~~ -> realai/server/legacy_api.py + shims + opt-in bridge (docs/SERVERS.md), 806640f
- ~~realai/craft.py vs realai/cli/craft.py~~ -> cli/craft.py canonical, realai/craft.py shim, cc38c58
- ~~local_models PEFT path~~ -> merged into realai/core/local_models.py, cc38c58

Open:

- REALAI_EXEC_UNGATED=1 escape hatch (restores ungated _run_tool exec for console sessions): keep or delete?
- Approval store path: set APPROVALS_STORE once so the Flask approval UI, the gate and approval_status share one file (UI defaults to cwd .approvals.json)
- craft CLI: tool_exec -> v3_orchestrator._run_tool write/exec now files approval requests too (human-operated CLI); exempt craft?
- realai.plugins.tools package import pulls core.security (missing in some envs) -> hive_executor cannot reach approval_store and denies everything (safe, but no pending request is filed)
- Point orchestrator voice_* tools / abilities/audio_speech at realai.voice_service (lab-first) instead of in-process provider?
- Make REALAI_SERVER_MERGED_ROUTES / REALAI_IMAGES_LOCAL_SDXL default on :8000?
- realai/start_realai.bat calls `realai.cli.realai_cli serve`, which does not exist in this tree
- realai/core/training/finetune.py plan default data dir (realai/core/datasets/processed) vs RealAI-gold main-realai (<repo>/training/data)
- agents/agents.py `AGENT_REGISTRY = property(...)` at module level (a property object, not a dict) was dropped by realai/core/agents/agents.py: confirm it stays dropped

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

## Not analyzed this pass (priority 9)

| canonical | other versions |
|---|---:|
| `realai/coding_agent.py` | 34 |
| `realai/api_server.py` | 31 |
| `realai/core/local_models.py` | 30 |
| `realai/plugins/sample_plugin.py` | 26 |
| `realai/server/router.py` | 23 |
| `realai/ui/realai_gui.py` | 22 |
| `realai/models/model_catalog.py` | 15 |
| `realai/server/orchestration.py` | 15 |
| `realai/tools.py` | 14 |
| `realai/server/memory_store.py` | 13 |
| `_quarantine/twins_20260926/realai__apps/api/main.py` | 12 |
| `realai/core/agents/supervisor.py` | 12 |
| `realai/core/agents/agents.py` | 11 |
| `realai/core/audit.py` | 11 |
| `realai/core/tools/code.py` | 11 |
| `realai/core/tools/file.py` | 11 |
| `realai/core/tools/registry.py` | 11 |
| `realai/core/tools/web3.py` | 11 |
| `_quarantine/twins_20260921/realai__plugins__plugins/plugin___init__.py` | 10 |
| `_quarantine/twins_20260926/realai__apps/api/routes/chat.py` | 10 |
| `realai/plugins/atomicfizz_coach/__init__.py` | 10 |
| `realai/plugins/atomicfizz_coach/abilities/__init__.py` | 10 |
| `realai/plugins/atomicfizz_coach/abilities/health.py` | 10 |
| `realai/scanners/promote_gold.py` | 10 |
| `realai/server/backends.py` | 10 |
| `realai/training/eval.py` | 10 |
| `realai/core/agents/critic.py` | 9 |
| `realai/core/agents/executor.py` | 9 |
| `realai/core/agents/planner.py` | 9 |
| `realai/core/agents/synthesizer.py` | 9 |
| `realai/core/agents/worker.py` | 9 |
| `realai/core/closed_loop.py` | 9 |
| `realai/api/index.py` | 8 |
| `realai/core/self_builder.py` | 8 |
| `realai/core/self_improvement.py` | 8 |
| `realai/plugins/effective_engine_main_coach/abilities/agents_bridge.py` | 8 |
| `realai/plugins/effective_engine_main_coach/abilities/repo_map.py` | 8 |
| `realai/sdk/python/realai_client.py` | 8 |
| `realai/core/identity.py` | 7 |
| `realai/core/training/extract_from_agent_tools.py` | 7 |
| `realai/core/web3/evm_backend.py` | 7 |
| `realai/core/web3/solana_backend.py` | 7 |
| `realai/plugins/tools/harden_repos.py` | 7 |
| `realai/recovery_registry.py` | 7 |
| `realai/router.py` | 7 |
| `realai/training/unsloth_train.py` | 7 |
| `_quarantine/twins_20260926/realai__modules__desktop_unique/examples_local_ai.py` | 6 |
| `realai/cli/craft.py` | 6 |
| `realai/cli/realai_cli.py` | 6 |
| `realai/plugins/device_selector.py` | 6 |
| `realai/plugins/tools/rollout_all_repos.py` | 6 |
| `realai/scripts/realai_full_loop_integrator_auto_fixed.py` | 6 |
| `realai/config/amd_inference.py` | 5 |
| `realai/core/inference/chat_pipeline.py` | 5 |
| `realai/plugins/effective_engine_main_coach/abilities/node_context.py` | 5 |
| `realai/plugins/smart_merge_realai.py` | 5 |
| `realai/scripts/setup_local_llama.py` | 5 |
| `realai/scripts/stack_health.py` | 5 |
| `realai/server/llama_cli_backend.py` | 5 |
| `realai/server/server_settings.py` | 5 |
| `realai/server/tools_runtime.py` | 5 |
| `realai/voice/tts_engine.py` | 5 |
| `_quarantine/twins_20260926/realai__apps/api/routes/audio.py` | 4 |
| `_quarantine/twins_20260926/realai__apps/api/routes/embeddings.py` | 4 |
| `_quarantine/twins_20260926/realai__apps/api/routes/health.py` | 4 |
| `_quarantine/twins_20260926/realai__apps/api/routes/models.py` | 4 |
| `_quarantine/twins_20260926/realai__apps/api/routes/tasks.py` | 4 |
| `_quarantine/twins_20260926/realai__apps/api/routes/voice_ws.py` | 4 |
| `_quarantine/twins_20260926/realai__apps/api/routes/web3.py` | 4 |
| `realai/mcp_server.py` | 4 |
| `realai/plugins/agent-tools-main/sanity_check.py` | 4 |
| `realai/server/app.py` | 4 |
| `realai/server/config.py` | 4 |
| `_quarantine/twins_20260924/realai_agents/router.py` | 3 |
| `realai/engine/__init__.py` | 3 |
| `realai/plugins/realai_clean_backup_coach/abilities/abilities_bridge.py` | 3 |
| `realai/plugins/realai_clean_backup_coach/abilities/modules_bridge.py` | 3 |
| `realai/plugins/realai_clean_backup_coach/abilities/packages_bridge.py` | 3 |
| `realai/plugins/realai_clean_backup_coach/abilities/plugins_bridge.py` | 3 |
| `realai/plugins/realai_clean_backup_coach/abilities/route_v1_audio_speech.py` | 3 |
| `realai/plugins/realai_clean_backup_coach/abilities/route_v1_audio_transcriptions.py` | 3 |
| `realai/plugins/realai_clean_backup_coach/abilities/route_v1_chat_completions.py` | 3 |
| `realai/plugins/realai_local_server.py` | 3 |
| `realai/scripts/catalog_good_code_roots.py` | 3 |
| `realai/scripts/find_self_improve_and_lost.py` | 3 |
| `realai/scripts/train_lora_local.py` | 3 |
| `realai/scripts/train_to_chat_gguf.py` | 3 |
| `realai/scripts/vulkan_runtime.py` | 3 |
| `realai/server/embeddings_backend.py` | 3 |
| `scripts/deep_promote_scan.py` | 3 |
| `_quarantine/twins_20260921/realai__plugins__plugins/plugin_test_realai.py` | 2 |
| `realai/core/training/finetune.py` | 2 |
| `realai/doctor.py` | 2 |
| `realai/lambda_embeddings_audio.py` | 2 |
| `realai/learn/scaffold.py` | 2 |
| `realai/local_media.py` | 2 |
| `realai/model_assets.py` | 2 |
| `realai/plugins/effective_engine_main_coach/abilities/fastify_context.py` | 2 |
| `realai/scripts/heal_cli.py` | 2 |
| `realai/training/llama_tools.py` | 2 |
| `realai/voice/lab_server.py` | 2 |
| `realai/workspace.py` | 2 |
| `realai/__init__.py` | 1 |
| `realai/__main__.py` | 1 |
| `realai/_v1_client.py` | 1 |
| `realai/agent_activity.py` | 1 |
| `realai/aura/reasoning.py` | 1 |
| `realai/bot/boot.py` | 1 |
| `realai/bot/live_exec.py` | 1 |
| `realai/bot/natural_mode.py` | 1 |
| `realai/bot/talk_easy.py` | 1 |
| `realai/core/metrics/metrics.py` | 1 |
| `realai/core/security/python_sandbox.py` | 1 |
| `realai/core/training/train_qwen_lora_directml.py` | 1 |
| `realai/examples/examples_limitless.py` | 1 |
| `realai/learn/pipeline.py` | 1 |
| `realai/model_registry.py` | 1 |
| `realai/plugins/tools/self_extend_tool.py` | 1 |
| `realai/plugins/tools/self_repair_tool.py` | 1 |
| `realai/scripts/exportable/realai_server.py` | 1 |
| `realai/server/inference.py` | 1 |
| `realai/training/self_data/__main__.py` | 1 |
| `realai/universe/dispatcher.py` | 1 |
| `realai/universe/doctor.py` | 1 |
| `realai/universe/hierarchy.py` | 1 |
| `realai/universe/knowledge_graph.py` | 1 |
| `realai/universe/mode.py` | 1 |
| `realai/universe/recipe_engine.py` | 1 |
| `realai/universe/registry.py` | 1 |
| `realai/voice/paths.py` | 1 |
