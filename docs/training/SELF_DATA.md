# Hive routing data, self-data loop, learning capture

RealAI is a hive: the model routes facts to tools, abilities and agents and answers from their output.
It does not answer RackUp rules, shot routes, chess moves or hardware advice from memory. The
`realai-sft-1.5b` spot-check (1/15) showed what happens otherwise: the model learns answer formats
and makes up the facts.

## Pieces

| piece | path | what it does |
|---|---|---|
| tool registry | `realai/hive_tools/__init__.py` | Qwen tool specs + read-only executors: `chess_engine`, `rackup_invoke` (pyramid_rules, rating_convert, league_validate, ledger_audit, payout_sanity, money_anomaly), `shot_lookup`, `device_profile`, `math_solver`, `data_analysis`, `ability_lookup`, `list_agents`, `route_to_agent`, `web_search`/`solana_read` (network; refused offline) |
| tool loop | `realai/hive_tools/tool_loop.py` | model -> `<tool_call>` -> execute -> tool message -> grounded answer (max 4 rounds) |
| orchestrator glue | `realai/hive_tools/orchestrator_hook.py` | opt-in tool loop on `/v1/chat/completions`; opt-in capture of chats and `/v1/tools/execute` |
| tool-call rows | `dataset_builder` source `tool_calls` | user -> tool call with the correct args -> REAL output (run at build time, offline) -> answer restating it |
| self-knowledge | source `self_knowledge` | abilities (LIVE/PARTIAL/STUB, path, modules), tools + args, agents, modules, identity. Rebuilt from the live code on every build, so it never goes stale |
| self-play | `python -m realai.training.self_data generate` | the hive writes questions per tool (default teacher: :8080 14B), runs them through the tool loop, verifies, then writes `datasets/_sources/hive_selfplay/selfplay-*.jsonl` |
| verifier | `realai/training/self_data/verify.py` | tool must succeed; chess move == Stockfish; numbers in the answer appear in tool output or question; routes match the catalogue; agent/ability named; optional LLM judge (`--judge`) |
| capture | `realai/training/self_data/capture.py` | opt-in log of real activity, tagged by project |
| improvement loop | `python -m realai.training.self_data improve` | spot-check + self-play failures -> per-tool weights (`generate --plan auto`) + `hive_selfplay/reports/improvement-*.md` |
| gate | `python -m realai.training.spotcheck` | 17 checks with the tool loop; `train_sft register --default` refuses below 80% |

## Runtime routing (opt-in, default off)

Turn it on in one of three ways: set `REALAI_TOOL_LOOP=1`, send the header `X-RealAI-Tool-Loop: 1`, or put
`"realai_tool_loop": true` in the body. Requests then go to `/v1/chat/completions` on :8001 and run the tool loop.
The backend defaults to the orchestrator's :8080. Set `REALAI_TOOL_LOOP_BASE=http://127.0.0.1:8081` or
`"realai_tool_loop_base"` to use the trained 1.5B instead. Tool calls are listed in `realai_meta.tool_calls`.
Without the opt-in, chat behaves exactly as before.

Small Qwen2.5 GGUFs (1.5B) on this Vulkan llama-server build must run with `-fa off`.
With flash attention on, they output only `////`. Always use `--jinja`, because it turns `<tool_call>` into `tool_calls`.

## Learning from all RealAI activity (opt-in capture)

Set `REALAI_CAPTURE=1` on the orchestrator (:8001). Every chat reply, tool-loop run and `/v1/tools/execute` call is then appended to
`REALAI_HOME/datasets/_sources/hive_traffic/<project>-<date>.jsonl`.

* **Project tag:** taken from the header `X-RealAI-Project` or the body `realai_project`
  (`rackup` = rackofchampions.com coach calls, `atomicfizz` = atomicfizzcaps.xyz overseer, `cli`, `chess`, `hive`, `realai`).
  If neither is set, it is inferred from the text. RackUp and Atomic Fizz backends should send the header.
* **Redaction:** a row is dropped if it holds a real secret (API keys, tokens, private keys) or mentions a seed phrase or private key.
  Emails, user names/paths, Solana/EVM wallet addresses, tx signatures and bearer tokens become placeholders.
* **Real money:** any row that mentions or calls payouts, transfers, sends, swaps, trades or mints is stored with `replay:false`.
  The verifier skips it, so it never becomes training data. No loop re-executes captured tool calls.
  Self-play only runs the read-only registry, offline: no Solana sends, no live trading, no writes outside `REALAI_HOME`.
* **To training data:** `python -m realai.training.self_data verify-traffic` runs the same verifier and appends
  accepted rows to `hive_selfplay/traffic-<date>.jsonl`. The `hive_selfplay` dataset source ingests them with dedupe.
  Plain chats without a tool call are rejected because they can't be proven grounded. Bare `/v1/tools/execute` captures
  (no answer) are kept only as coverage logs.

## Loop

```
spotcheck -> improve (weights + report) -> generate --plan auto (verified rows) -> verify-traffic
          -> dataset_builder --config config/dataset_builder.hive.pc.json -> train_sft -> spotcheck ...
```

## Wire-audit tools (2026-10-12, branch feat/hive-wire-audit)

Twelve read-only tools were added to `realai/hive_tools/extended.py`. Each one is deterministic for the same arguments, and none of them uses the network, sends anything or touches money:

- **RackUp:** `rating_update_preview`, `matchmaking_suggest`, `rating_intel`, `game_rules`, `coach_drill` and `hall_context`. All of them call `realai/plugins/rackup_coach`, which is the canonical RackUp code.
- **Self-knowledge:** `module_lookup`, `plugin_lookup`, `plugin_registry_list` and `organs_hive_status`. These read `abilities/*_surface.py`, `realai.plugin_registry` and `modules.organs`.
- **Local stores:** `memory_search` and `approval_status`. Each reads a private temp copy of its source, either `memory/hive/memory.sqlite3` or `.approvals.json`. `approval_status` has no write path.
- **Skipped:** `knowledge_query`. The knowledge graph has no persisted store, so there's nothing to ground an answer in.

`route_to_agent` now hands off through `realai.orchestration.hive_router.run_cycle(dry_run=True)`. That resolves the model, the routes and the pipeline stages exactly like a live cycle, but executes nothing.

**Verifier.** For each of these tools the verifier re-runs the same executor with the same arguments. The row is rejected if the result differs (`recompute_mismatch`) or if the answer leaves out the key fact (`<tool>_fact_missing`).

**improve.** Each new tool gets weight ≥ 2.5 until it has 40 accepted rows.

**Spot-check.** Use `python -m realai.training.spotcheck --suite extended` to score the new tools. The default `core` suite, the `register --default` gate and the comparable MODELS.md score are unchanged. Extended scores are stored as `tools_extended`.

### Wire-in batch 2026-10-16 (`realai/hive_tools/wired.py`)

Seven more read-only / dry-run tools, in `NEW_TOOLS` (weak weighting until 40 accepted rows), with templates, seeds,
`ACCEPT_TOOLS` routing, verifier key facts (`hive_tools.key_facts`) and `--suite extended` spot-checks:
`memory_stats`, `agent_pipeline_plan`, `hive_routes_status`, `payout_check` (never authorizes a payout),
`tool_registry_lookup`, `self_heal_status` (report only), `executive_goals` (snapshot; never ticks).
The live tool loop only offers wire-audit tools with `REALAI_HIVE_TOOLS=1` (`hive_tools.live_specs()`).
