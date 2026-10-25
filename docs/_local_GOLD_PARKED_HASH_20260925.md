# GOLD parked vs live hash compare (2026-09-25)

Read-only basename+sha256 compare. **No files copied or merged onto live.** No git add/commit/push.

## Scope

| Field | Value |
|---|---|
| Generated (PT) | 2026-09-25 20:07:23 -07:00 |
| Shelves (source) | `C:\RealAI-gold\orphans\_parked\` folders `2026-09-07*` and `2026-09-08*` only |
| Live gold (dest authority) | `C:\RealAI-clean` branch tip as-is |
| Live branch | `live/realai-clean-20260911` @ `839ce968` |
| Live tip | 839ce968 | 2026-09-25 19:43:23 -0700 | Park phase 3 duplicate import paths under twins_20260926 (#139) |
| Product exts | `*.py` `*.js` `*.ts` `*.html` `*.md` |
| Skips | `node_modules`, `C__*`, `.before`, HF/venv, tokenizer dumps, blobs >5MB |
| Live excludes | `_quarantine`, `recovered`, `imports`, `.learn_cache`, `.venv*`, `site-packages` |
| Cap | ~80 files (actual compared: 22) |
| Files copied | **0** |

## Parked buckets

| Folder | File count |
|---|---:|
| `2026-09-07-gpu-ctx` | 2 |
| `2026-09-07-orch2` | 2 |
| `2026-09-07-universe` | 8 |
| `2026-09-07-voice-exec` | 1 |
| `2026-09-08-cors-voice` | 1 |
| `2026-09-08-hive-agents-ui` | 2 |
| `2026-09-08-multi-agent-liveexec` | 1 |
| `2026-09-08-multi-agent-worker` | 1 |
| `2026-09-08-next-level` | 5 |
| `2026-09-08-realai-gateway` | 1 |
| `2026-09-08-voice-cors` | 1 |
| `2026-09-08-xtts-console` | 1 |
| **Total** | **26** |

### Skipped `.before` snapshots (not compared)

- `2026-09-08-hive-agents-ui\agent_activity.before.py` (16102 bytes)
- `2026-09-08-hive-agents-ui\v3_orchestrator.before-multi-pulse-065217.py` (143948 bytes)
- `2026-09-08-multi-agent-liveexec\v3_runtime_bridge.before-vscode-harden-064437.py` (79621 bytes)
- `2026-09-08-multi-agent-worker\v3_runtime_bridge.before-034344.py` (72562 bytes)

## Class counts

| Class | Count |
|---|---:|
| IDENTICAL_NOISE | 0 |
| KEEP_LIVE | 17 |
| PROMOTE_CANDIDATE | 0 |
| UNIQUE_NO_LIVE | 5 |
| **Compared** | **22** |

## PROMOTE_CANDIDATE (0)

_None._

## UNIQUE_NO_LIVE (5)

### `shim_before_v3_orchestrator.py` — UNIQUE_NO_LIVE

| | |
|---|---|
| Parked | `2026-09-08-next-level\shim_before_v3_orchestrator.py` |
| Parked size | 612 |
| Parked sha256 | `5879e99173b8c81a8f094530e6aa918dddb49cc40542df114c4278b55b2d3c94` |
| Evidence | no live basename/path-hint or content hash under clean preferred tree |

### `deploy_fabric.py` — UNIQUE_NO_LIVE

| | |
|---|---|
| Parked | `2026-09-08-next-level\deploy_fabric.py` |
| Parked size | 7714 |
| Parked sha256 | `b080effc42e36b9336484b389fc1d0c17242e40acd89bcfe254732671df875d7` |
| Evidence | no live basename/path-hint or content hash under clean preferred tree |

### `meta_router_before_fabric.py` — UNIQUE_NO_LIVE

| | |
|---|---|
| Parked | `2026-09-08-next-level\meta_router_before_fabric.py` |
| Parked size | 7703 |
| Parked sha256 | `fe1a53d7f8e427b12060b7a2ba2979d492e98df07e0e12911bc23fb51b6bbdd7` |
| Evidence | no live basename/path-hint or content hash under clean preferred tree |

### `cli-hive-commands-world.py` — UNIQUE_NO_LIVE

| | |
|---|---|
| Parked | `2026-09-07-universe\cli-hive-commands-world.py` |
| Parked size | 2651 |
| Parked sha256 | `b652cd8b1c971c38863067275f17d98b7da932dc558a65fd94f47d4b99a05259` |
| Evidence | no live basename/path-hint or content hash under clean preferred tree |

### `shim_before_realai_orchestrator.py` — UNIQUE_NO_LIVE

| | |
|---|---|
| Parked | `2026-09-08-next-level\shim_before_realai_orchestrator.py` |
| Parked size | 481 |
| Parked sha256 | `4bf8b5abc5ab4b9396a7a790d3fce0c19c36d73bfa2dea0baeb0f391ae9c5742` |
| Evidence | no live basename/path-hint or content hash under clean preferred tree |

## KEEP_LIVE (17)

### `v3_orchestrator.py` — KEEP_LIVE

| | |
|---|---|
| Parked | `2026-09-08-realai-gateway\v3_orchestrator.py` |
| Parked size | 139681 |
| Parked sha256 | `11639ee509c6a01a1802cc018d5cfd59534c23006c0448e3901ebdf9859a9eee` |
| Live | `realai\orchestration\v3_orchestrator.py` |
| Live size | 164699 |
| Live sha256 | `f93ecf8bee8fbc38301fe2af10ff45d805675b3f84532018ca5b4571a4f1f711` |
| Match | basename |
| Evidence | live size 164699 >= parked 139681; live=realai\orchestration\v3_orchestrator.py (auth=0, basename) |

### `v3_orchestrator.py` — KEEP_LIVE

| | |
|---|---|
| Parked | `2026-09-08-xtts-console\v3_orchestrator.py` |
| Parked size | 136346 |
| Parked sha256 | `283f24ce10387f254639e734abac3c7fbaf27fbe2262ac1345feb1c87d3f3850` |
| Live | `realai\orchestration\v3_orchestrator.py` |
| Live size | 164699 |
| Live sha256 | `f93ecf8bee8fbc38301fe2af10ff45d805675b3f84532018ca5b4571a4f1f711` |
| Match | basename |
| Evidence | live size 164699 >= parked 136346; live=realai\orchestration\v3_orchestrator.py (auth=0, basename) |

### `v3_orchestrator.py` — KEEP_LIVE

| | |
|---|---|
| Parked | `2026-09-07-orch2\v3_orchestrator.py` |
| Parked size | 134482 |
| Parked sha256 | `186d0551e6fc2c5134b3595b4c7a4165c42b544ff6f21d84cb7475664f3825c8` |
| Live | `realai\orchestration\v3_orchestrator.py` |
| Live size | 164699 |
| Live sha256 | `f93ecf8bee8fbc38301fe2af10ff45d805675b3f84532018ca5b4571a4f1f711` |
| Match | basename |
| Evidence | live size 164699 >= parked 134482; live=realai\orchestration\v3_orchestrator.py (auth=0, basename) |

### `craft.py` — KEEP_LIVE

| | |
|---|---|
| Parked | `2026-09-07-orch2\craft.py` |
| Parked size | 130497 |
| Parked sha256 | `1e42da55d1dc511428980410d19a7e5b302e07be42e3bd58c48a8b1805ee8263` |
| Live | `realai\cli\craft.py` |
| Live size | 159991 |
| Live sha256 | `52aa0b47443682e20693fdfa0c9f7fc911b057595a3938730900caf26ea43cbc` |
| Match | basename |
| Evidence | live size 159991 >= parked 130497; live=realai\cli\craft.py (auth=6, basename) |

### `scripts__vulkan_runtime.py` — KEEP_LIVE

| | |
|---|---|
| Parked | `2026-09-07-gpu-ctx\scripts__vulkan_runtime.py` |
| Parked size | 9378 |
| Parked sha256 | `68f623faf31f5cc8c5df9b7c4d41d7af362f968736cd6cee7989d2b077b7e371` |
| Live | `realai\scripts\vulkan_runtime.py` |
| Live size | 8258 |
| Live sha256 | `af6ce3180294a19faf2be8f5dcd18e09f9168d3a5015af2df685a4fc95fa8e11` |
| Match | path-hint |
| Evidence | parked slightly larger (9378>8258, +1120) but no unique defs / not clearly fuller; live=realai\scripts\vulkan_runtime.py (auth=10, path-hint) |

### `realai__scripts__vulkan_runtime.py` — KEEP_LIVE

| | |
|---|---|
| Parked | `2026-09-07-gpu-ctx\realai__scripts__vulkan_runtime.py` |
| Parked size | 8375 |
| Parked sha256 | `ed3c19194351a30c650a20bb2bb864c8c7e1fbcc28f6a4647282ca451d14cb4a` |
| Live | `realai\scripts\vulkan_runtime.py` |
| Live size | 8258 |
| Live sha256 | `af6ce3180294a19faf2be8f5dcd18e09f9168d3a5015af2df685a4fc95fa8e11` |
| Match | path-hint |
| Evidence | parked slightly larger (8375>8258, +117) but no unique defs / not clearly fuller; live=realai\scripts\vulkan_runtime.py (auth=10, path-hint) |

### `lab_server.py` — KEEP_LIVE

| | |
|---|---|
| Parked | `2026-09-08-voice-cors\lab_server.py` |
| Parked size | 6555 |
| Parked sha256 | `d92cc8ad5010def9164d30b583eab65a5530ef027a4d34754059ec1cea502300` |
| Live | `realai\voice\lab_server.py` |
| Live size | 7006 |
| Live sha256 | `1ba79ed3a0fc5f0f2feb3a3b92b2a890b14df8b84af754433147187af138f8cf` |
| Match | basename |
| Evidence | live size 7006 >= parked 6555; live=realai\voice\lab_server.py (auth=10, basename) |

### `lab_server.py` — KEEP_LIVE

| | |
|---|---|
| Parked | `2026-09-08-cors-voice\lab_server.py` |
| Parked size | 6470 |
| Parked sha256 | `58b18694b69ce345c55d38c521496b96c625aa465b490b4ddcb1889e47470ab8` |
| Live | `realai\voice\lab_server.py` |
| Live size | 7006 |
| Live sha256 | `1ba79ed3a0fc5f0f2feb3a3b92b2a890b14df8b84af754433147187af138f8cf` |
| Match | basename |
| Evidence | live size 7006 >= parked 6470; live=realai\voice\lab_server.py (auth=10, basename) |

### `paths.py` — KEEP_LIVE

| | |
|---|---|
| Parked | `2026-09-07-voice-exec\paths.py` |
| Parked size | 5824 |
| Parked sha256 | `bbc40ce78aaa7982f586d5c0dd79d4a75b3040ddf1a4985b56d06fb4fbcef0b4` |
| Live | `realai\voice\paths.py` |
| Live size | 5745 |
| Live sha256 | `108151d009aeb98073af4ebf4d06a219869102ffbe27b6a08cceb0b0023447c2` |
| Match | basename |
| Evidence | parked slightly larger (5824>5745, +79) but no unique defs / not clearly fuller; live=realai\voice\paths.py (auth=10, basename) |

### `registry.py` — KEEP_LIVE

| | |
|---|---|
| Parked | `2026-09-07-universe\registry.py` |
| Parked size | 3151 |
| Parked sha256 | `28b64cdff5d23177b281f98edbfa83ad400483ad1ed49e3cc121c4678dff3a39` |
| Live | `realai\universe\registry.py` |
| Live size | 3076 |
| Live sha256 | `3aeeedb38701258600ad34ad14590cf14f96b78264ac78d8d3971e9363072e1e` |
| Match | basename |
| Evidence | parked slightly larger (3151>3076, +75) but no unique defs / not clearly fuller; live=realai\universe\registry.py (auth=8, basename) |

### `doctor.py` — KEEP_LIVE

| | |
|---|---|
| Parked | `2026-09-07-universe\doctor.py` |
| Parked size | 1811 |
| Parked sha256 | `cd9d364cef40b41ad157fb37d28d969527efb27ba10863c85e74eed12680d7cb` |
| Live | `realai\universe\doctor.py` |
| Live size | 1846 |
| Live sha256 | `255952cd0dc6c8cc6fc9d567165509c3aaa56b20cbe87db0a9393e74dd7e08ab` |
| Match | basename |
| Evidence | live size 1846 >= parked 1811; live=realai\universe\doctor.py (auth=8, basename) |

### `mode.py` — KEEP_LIVE

| | |
|---|---|
| Parked | `2026-09-07-universe\mode.py` |
| Parked size | 1678 |
| Parked sha256 | `0733ba9aff3ed68dce49e06955ea68aa4eddefd875bfc2d165320f5d3ee61abd` |
| Live | `realai\universe\mode.py` |
| Live size | 3188 |
| Live sha256 | `a241363927fc558746ba361cd0452748838c51f721a256ab6b371640e6ea1d96` |
| Match | basename |
| Evidence | live size 3188 >= parked 1678; live=realai\universe\mode.py (auth=8, basename) |

### `dispatcher.py` — KEEP_LIVE

| | |
|---|---|
| Parked | `2026-09-07-universe\dispatcher.py` |
| Parked size | 1506 |
| Parked sha256 | `1c9a5e0537bf1de0b2961cb007cd3b9b7176beb5ba9932cdd1e7690e269c1ac4` |
| Live | `realai\universe\dispatcher.py` |
| Live size | 1500 |
| Live sha256 | `74605caf8eaa590938631b91095b55e17b74a1a9a2b074a34e4b918dec1c2be1` |
| Match | basename |
| Evidence | parked slightly larger (1506>1500, +6) but no unique defs / not clearly fuller; live=realai\universe\dispatcher.py (auth=8, basename) |

### `knowledge_graph.py` — KEEP_LIVE

| | |
|---|---|
| Parked | `2026-09-07-universe\knowledge_graph.py` |
| Parked size | 1498 |
| Parked sha256 | `3611c902508f17f3c2b93f3e5618baea9678c655bb1f45cf0c6a37a70443905f` |
| Live | `realai\universe\knowledge_graph.py` |
| Live size | 1428 |
| Live sha256 | `1b2f523f4d095e29d10314255260a9b8b6bd8ead23446e8be32d61efd2a45cdb` |
| Match | basename |
| Evidence | parked slightly larger (1498>1428, +70) but no unique defs / not clearly fuller; live=realai\universe\knowledge_graph.py (auth=8, basename) |

### `hierarchy.py` — KEEP_LIVE

| | |
|---|---|
| Parked | `2026-09-07-universe\hierarchy.py` |
| Parked size | 602 |
| Parked sha256 | `65a29602082c4d9a0e102a922e792ae59448ffd400e95ac291d95718618e9f2c` |
| Live | `realai\universe\hierarchy.py` |
| Live size | 537 |
| Live sha256 | `e075135d134a36d1341162a228998ddbfd4ce28fc87607ecde408fccfcc1f0ef` |
| Match | basename |
| Evidence | parked slightly larger (602>537, +65) but no unique defs / not clearly fuller; live=realai\universe\hierarchy.py (auth=8, basename) |

### `recipe_engine.py` — KEEP_LIVE

| | |
|---|---|
| Parked | `2026-09-07-universe\recipe_engine.py` |
| Parked size | 421 |
| Parked sha256 | `aa5f14d130ea19487a7f37ba336a9203cdfda26be4a131da3d8edce8855b40ec` |
| Live | `realai\universe\recipe_engine.py` |
| Live size | 391 |
| Live sha256 | `cbe95b0bdc73373f586c5f6c751b45690e56793e92c8d9030690f2ba2bc80a82` |
| Match | basename |
| Evidence | parked slightly larger (421>391, +30) but no unique defs / not clearly fuller; live=realai\universe\recipe_engine.py (auth=8, basename) |

### `watchers__init__.py` — KEEP_LIVE

| | |
|---|---|
| Parked | `2026-09-08-next-level\watchers__init__.py` |
| Parked size | 54 |
| Parked sha256 | `4ed93e8acb79e22fc5545101fed22c67cd122a9e7600a2d5da94092154618942` |
| Live | `realai\executive\watchers\__init__.py` |
| Live size | 680 |
| Live sha256 | `da88688db865435ca96f90ee3a3c63933a835529f20e1fd89a7e396945eb971a` |
| Match | path-hint |
| Evidence | live size 680 >= parked 54; live=realai\executive\watchers\__init__.py (auth=9, path-hint) |

## IDENTICAL_NOISE (0)

_None._

## Notes

- Live path preference: `realai\orchestration\v3_orchestrator.py`, `realai\orchestration\v3_runtime_bridge.py`, then `realai\` (with `realai\cli\craft.py` preferred over `realai\craft.py`), `abilities\`, `modules\organs\`, `apps\vscode\`, `agent_tools\`, `agents\`.
- Flattened parked names (`scripts__vulkan_runtime.py`, `watchers__init__.py`) resolved via path-hint when needed.
- PROMOTE_CANDIDATE: parked larger AND (unique def/class symbols vs live match, OR size delta > 2048).
- KEEP_LIVE: diff but live wins (larger and/or gold-path authority).
- **Zero files copied** onto `C:\RealAI-clean`. Report-only write.


## UNIQUE file judgments

Read-only judgment pass (2026-09-25 ~20:10 PT). No copy/merge/git. Hive gold remains `realai/orchestration/v3_orchestrator.py`; bridge `v3_runtime_bridge.py`; coaches untouched.

### 1. `deploy_fabric.py` — KEEP_SHELF

| | |
|---|---|
| Parked | `2026-09-08-next-level\deploy_fabric.py` (7714, sha256 `b080effc…`) |
| Purpose | One-shot deployer: zlib+b64 payloads write `realai/memory/fabric.py`, `__init__.py`, `FABRIC.md`, touch `state/memory/fabric.jsonl`. |
| Top-level | `PAYLOADS`, `decode`; script body (side-effect writes). |
| Live | `realai/memory/fabric.py` already present; **embedded fabric sha256 == live** (`350d586c…`). |
| Why | Obsolete deploy tool. Re-running would overwrite live memory package. Payload already applied. |

### 2. `meta_router_before_fabric.py` — KEEP_SHELF

| | |
|---|---|
| Parked | `2026-09-08-next-level\meta_router_before_fabric.py` (7703, `fe1a53d7…`) |
| Purpose | Pre-fabric meta-router vertical slice: classify → route → memory read/write hooks (no model invoke). |
| Top-level | `SECRET_PATTERNS`, `RoutingDecision`, `_cloud_allowed`, `_has_secrets`, `classify_task`, `route_task`, `memory_read_hook`, `memory_write_hook`, `plan_call`. |
| Live | `realai/meta_router.py` (12070) — evolved successor with `_looks_like_work_loop`, `_foreign_inspect_ask`. Hash differs. |
| Why | Collision with live gold predecessor snapshot; live is strictly newer. Do not promote over live. |

### 3. `cli-hive-commands-world.py` — KEEP_SHELF

| | |
|---|---|
| Parked | `2026-09-07-universe\cli-hive-commands-world.py` (2651, `b652cd8b…`) |
| Purpose | Early Hive CLI `world` group: `status` / `show` / `query` over universe + world_inspector. |
| Top-level | `_ws`, `world_group`, `world_status`, `world_show`, `world_query`. |
| Live | `realai/cli/hive/commands/world.py` (5904) already registered in `app.py`; adds `doctor`, `architect`, `registry`, `graph`, `route`. SelfBuilder is separate package-root shim → `realai.core.self_builder`. |
| Why | Superseded subset of live world CLI. Orphan experiment slice; no promote. |

### 4. `shim_before_v3_orchestrator.py` — KEEP_SHELF

| | |
|---|---|
| Parked | `2026-09-08-next-level\shim_before_v3_orchestrator.py` (612, `5879e991…`) |
| Purpose | Package-root re-export shim: `realai.v3_orchestrator` → `realai.orchestration.v3_orchestrator`. |
| Top-level | star-import + `main`; `__main__` exit. |
| Live | `realai/v3_orchestrator.py` (756) — same role plus `sys.path` bootstrap. Hash differs. Gold logic stays in `orchestration/v3_orchestrator.py`. |
| Why | Obsolete shim snapshot. Coach/gold risk if treated as orch gold; live shim already supersedes. |

### 5. `shim_before_realai_orchestrator.py` — KEEP_SHELF

| | |
|---|---|
| Parked | `2026-09-08-next-level\shim_before_realai_orchestrator.py` (481, `4bf8b5ab…`) |
| Purpose | Package-root shim for `realai.realai_orchestrator` → gold v3 orchestrator. |
| Top-level | star-import + `main`; `__main__` exit. |
| Live | `realai/realai_orchestrator.py` (609) with path bootstrap. Hash differs. |
| Why | Obsolete shim; live is newer. Never overwrite coaches / orch gold. |

### Verdict summary

| File | Verdict | Suggested live path if promote |
|---|---|---|
| deploy_fabric.py | KEEP_SHELF | — (do not re-run) |
| meta_router_before_fabric.py | KEEP_SHELF | — (live `realai/meta_router.py` wins) |
| cli-hive-commands-world.py | KEEP_SHELF | — (live `cli/hive/commands/world.py` wins) |
| shim_before_v3_orchestrator.py | KEEP_SHELF | — (live `realai/v3_orchestrator.py` wins) |
| shim_before_realai_orchestrator.py | KEEP_SHELF | — (live `realai/realai_orchestrator.py` wins) |

**PROMOTE count: 0.** All five UNIQUE_NO_LIVE basenames are historical snapshots or one-shot deployers already reflected (or superseded) on live.

