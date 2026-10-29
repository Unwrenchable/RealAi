# RealAI One-Spine Plan

> **WARNING: two servers, one default port.** The orchestrator and `realai/server/legacy_api.py` (started as `python -m realai.api_server`) both default to **8001**. Until phase 6c, start the API server with `PORT=8000`. Easy to miss in local testing.

Status: **PLAN ONLY**. No code moves until travis approves it. Every path below was checked against `origin/main` @ `7a74abd`; main has since moved to `2f445c7`. Paths marked *(PR #210)* exist only on that open PR. Target paths (`realai/core/brain/`, `realai/core/permissions/`, `realai/core/memory/`, `realai/core/tasks/`, `packages/sdk`, `tests/catalog_evals/`, `docs/spine/*.csv`) are proposals and do not exist yet. Bare filenames in a row are relative to the directory named in that row.

**Goal:** RealAI should feel like one integrated assistant: one brain, one ability registry, one permission gate, one memory, one task system, one API/SDK. Right now it is a set of separate modules.

**Target layout**

| Target | Holds |
|---|---|
| `realai/core/` | brain loop, permission and approval layer, memory service, task runner, registry runtime |
| `realai/abilities/*` | one package per ability, implementing the ability contract |
| `apps/*` | `apps/api` (the one /v1 API), `apps/vscode`, `apps/dashboard`, plus voice and widget clients |
| `packages/sdk` | the one TS SDK, merged from `packages/realai-sdk` and `packages/sdk-ts` |

**Ground rules for every phase:** one small PR each, with acceptance tests. Stage paths explicitly. Open the PR but don't merge it; travis or Chief merges. Security reviews anything touching auth, tools, files, network or money. Archive means a move to `D:\ARCHIVE`, hash-verified, and only with travis's GO. Never touch `.env*`, `keys/` or `_git_rescue`. Never switch the default model. `trading.live` stays `false`. The console UI and voice trainer UI are not touched.

---

## 1. One brain loop

**Core:** `realai/orchestration/v3_orchestrator.py`. It already serves the full `/v1/*` surface: chat, abilities, tools/execute, tasks, hive, learn, training, workspace. The orchestrator runs on :8001.

**Current orchestrators and verdicts**

| Path | What it is today | Verdict |
|---|---|---|
| `realai/orchestration/v3_orchestrator.py` | canonical brain | **CORE**, moves to `realai/core/brain/` |
| `realai/core/orchestration/v3_orchestrator.py` | `import *` shim to the core | keep as shim, then archive |
| `realai/v3_orchestrator.py` | shim to the core | keep as shim (entry point), then archive |
| `realai/realai_orchestrator.py`, `realai/orchestration/realai_orchestrator.py` | shims | archive |
| `realai/orchestration/v3_runtime_bridge.py`, `realai/v3_runtime_bridge.py` (shim) | runtime and workspace guards | **CORE** (permission layer, §3) |
| `realai/orchestration/orchestrator.py`, `realai/core/orchestration/orchestrator.py`, `realai/core/orchestrator.py`, `realai/orchestrator.py` | older generic orchestrators | diff, then archive (plugin only if unique logic is found) |
| `realai/orchestration/legacy_orchestrator.py` | legacy | archive |
| `realai/orchestration/unified_orchestrator.py`, `realai/unified_orchestrator.py` | earlier "unify" attempt | archive after diff |
| `realai/orchestration/nest_orchestrators.py`, `realai/nest_orchestrators.py`, `realai/orchestrators/nest_orchestrators.py`, `abilities/nest_orchestrators.py`, `modules/orchestrators/nest_orchestrators.py` | nesting helper, 5 copies | one becomes a **plugin**, archive 4 |
| `realai/orchestration/hive_router.py`, `realai/core/orchestration/hive_router.py`, `core/orchestration/hive_router.py`, `realai/core_hive_router.py` | hive routing | **plugin** `realai/abilities/hive/`, archive dups |
| `realai/orchestration/hive_guard.py` | hive guard | **CORE** (permission layer) |
| `realai/hive_orchestrator.py`, `realai/realai_hive_orchestrator.py`, `abilities/hive_orchestrator.py`, `repo_tools/realai_hive_orchestrator.py` | hive orchestration | **plugin** (hive), archive dups |
| `realai/orchestration/{agent,pipeline,tools,surface,memory,tts_routing}.py` and the `realai/core/orchestration/` copies | helpers | keep the `realai/orchestration` copy, which moves to core; archive the dup copies |
| `realai/agent_runtime/orchestrator_agent_runtime.py` | agent runtime | **plugin** (agents) |
| `realai/orchestrators/*`: `nested_realai_v3_orchestrator.py`, `realai__v3_orchestrator.py`, `orchestrator_router.py`, `orchestrator_overmind_runner.py`, `orchestrator_self_improvement.py`, `orchestrator_solana.py`, `orchestration.py`, `orchestrator_orchestration.py`, `realai-ish_test_orchestration.py` | nested and recovered copies | archive. `self_improvement` goes to the `self_evolving` plugin and `solana` to the trading plugin, but only if a diff shows unique code |
| `modules/orchestrators/*` (about 30 files incl. `_19/_71/_100/_101/_127/_128/_29/_81` numbered variants, `orchestration_gold__orchestrator.py`, `v3_orchestrator__realai.py`) | recovery dump | archive all |
| `scripts/exportable/orchestrator_{overmind_runner,router,solana}.py`, `scripts/exportable/variants/nested_realai_v3_runtime_bridge.py`, `realai/scripts/exportable/variants/nested_realai_v3_runtime_bridge.py` | exported variants | archive |
| `realai/orchestrator/run.ts` | TS runner | review; likely archive |
| `realai/server/legacy_api.py` (started via the `realai/api_server.py` shim; defaults to `PORT=8001`, so run it with `PORT=8000` until phase 6c) | second server (chat, models) | keep as the Render/Vercel entry until §6 phase 6c, then make it a thin proxy to the core |

**Phases**
- **1a** Inventory PR: add `docs/spine/orchestrators.csv` (path, sha256, importers, verdict). *Acceptance:* a script reproduces the CSV from the tree, and every path in it exists.
- **1b** **CRITICAL PATH.** Import-graph test (many duplicates are `import *` or path-based imports). It must land and stay green **before ANY archive batch**, in every section; otherwise broken importers surface only after a GO. Import-graph test: a test asserts that no production module imports an archive-verdict file. *Acceptance:* the test passes on main (fix importers first, or keep shims).
- **1c** Move the core to `realai/core/brain/`, leaving shims at the old paths. *Acceptance:* the full suite passes in CI, `python -m realai.v3_orchestrator` boots on :8001, and `/v1/abilities` returns the same JSON as before.
- **1d** Archive batch (needs GO): move to `D:\ARCHIVE`, write a sha256 manifest, verify, then remove from the tree in a PR. *Acceptance:* the hash manifest verifies and CI is green.

## 2. One ability contract

**Registry:** `realai/ability_catalog.py` (about 1,500 lines) is currently a scanner and report builder (`build_catalog`, `save_catalog`, `coverage_summary`), not a runtime. The duplicate copies are `realai/plugins/ability_catalog.py` (shim), `abilities/ability_catalog.py` and `realai/plugins/related/ability_catalog.py`.

**Contract** (one dataclass in a **new, proposed** `realai/core/registry.py`; it does not exist yet):

```
name, title, version
inputs: JSON Schema       outputs: JSON Schema
permission: read | write | approval     # approval = files/network/money mutations
status: LIVE | PARTIAL | STUB           # LIVE only with an end-to-end proof (team rule relayed by Chief; adopted here as this plan's proposed rule)
handler: callable         eval: path to catalog eval case(s)
```

**Phases**
- **2a** Add the dataclass and a `register()`/`get()` API in `realai/ability_catalog.py`, generated from the existing entries with no behaviour change. *Acceptance:* every current entry (64 LIVE and 14 PARTIAL at #212) loads, and the schema is validated in a test.
- **2b** Route `/v1/abilities` and `/v1/abilities/run` in `v3_orchestrator.py` through the registry. *Acceptance:* identical listing, and running an unknown ability returns an error, not a fallback.
- **2c** Move abilities into `realai/abilities/<name>/` one at a time (the top-level `abilities/*.py` and `realai/abilities/` are the sources). *Acceptance:* each move has its own test, and the catalog status is unchanged.
- **Archive:** `abilities/ability_catalog.py`, `realai/plugins/related/ability_catalog.py`, and `abilities/from_accident/*`.

## 3. One permission and approval layer

**Builds on:** #195 `realai/orchestration/tool_auth.py` (gated `/v1/tools/execute`), `realai/core/approval_gate.py` (workspace resolve, `_money_check`, edit/write previews, audit log), `realai/orchestration/v3_runtime_bridge.py` workspace guards, and #210 *(PR #210)*: the denylist, fail-closed `REALAI_TOOLS_WORKSPACE_ROOT`, `REALAI_TOOLS_ALLOW`, O_NOFOLLOW walks, 64 KB read and 256 KB edit caps, and approvals bound to the file and hash. Docs: `docs/TOOLS_AUTH.md`, `docs/APPROVAL_GATE.md`.

**Target:** `realai/core/permissions/` is the only path to files, network and money. Each ability's `permission` field decides read (guarded), write (guarded plus allow-list) or approval (preview, human approve, hash-bound execute). Money actions are always approval, and `trading.live` stays `false`; this layer never flips it.

**Duplicates:** `abilities/approval_store.py`, `abilities/approval_ui.py`, `realai/plugins/tools/approval_store.py`, `realai/plugins/tools/approval_ui.py`, `realai/plugins/tools/tools/approval_{store,ui}.py`, `realai/hive_tools/approvals.py`, `realai/core/approvals_config.py` (merge the config into the core). Archive the dups after diffing.

**Phases**
- **3a** Land #210 (in flight, with Security).
- **3b** One `check(ability, action, args)` entry point. *Acceptance:* a test that grep-asserts no `open(..., 'w')`, `requests`/`httpx` or wallet signing outside `realai/core/permissions` in production code (allow-list of exemptions checked in). Security review.
- **3c** Network egress through the layer (local-only by default, no external keys). *Acceptance:* a network-permission test is denied by default. Security review.
- **3d** Money path: trading and wallet calls go through approval. *Acceptance:* tests prove `trading.live=false` blocks execution even after approval. Security review.

## 4. One memory service

**Current state is heavily duplicated.** `realai/memory/` alone holds `memory.py`, `memory_store.py`, `sqlite_memory.py`, `aura_memory.py`, `hive_memory.py` and `memory_learning.py`, plus nested copies (`memory/memory/`, `memory/engine/`, `memory/orchestration*/`, `memory/recycle_py*/`, `memory/C_realai_server/`, `memory/realai2_server/`, `memory/server/`). Elsewhere: `realai/server/memory_store.py`, `realai/orchestration/memory.py`, `realai/core/orchestration/memory.py`, `realai/engine/memory*.py`, `realai/agentx/engine/memory.py`, `realai/aura/memory.py`, `agents/hive/memory.py`, `abilities/hive_memory.py`, `abilities/memory_learning.py`, `modules/organs/memory_ecosystem/*` and `realai/memory/memory_ecosystem/*`. World model: `realai/core/world_model.py`, `core/world_model.py`, `realai/world_model.py`, and more than 20 copies under `realai/world_model/**` plus `world_model_merger.py`. Profiles: `realai/profiles/default.json`, `realai/server/profiles/default.json`, `realai/core/device_profile.py`. Journal: no dedicated module was found on main; **open decision D4**.

**Target:** `realai/core/memory/` with one store (`realai/memory/sqlite_memory.py` is the candidate) and four namespaces: `profile`, `journal`, `hive`, `world`. One API: `put/get/search/forget`, routed through permissions for writes.

**Phases**
- **4a** Inventory with sha256 values. Identical copies are marked archive. The inventory also flags **schema and semantic divergence** (sqlite tables, columns, keys; JSON/dict keys; differing read/write semantics) between the candidate store and every world-model/memory copy, not just identical hashes. *Acceptance:* the CSV reproduces.
- **4b** Facade `realai/core/memory/__init__.py` over the existing sqlite store. *Acceptance:* round-trip tests per namespace.
- **4c** Point the orchestrator memory calls at the facade. *Acceptance:* the existing memory tests pass, and there's one DB file.
- **4d** World model: pick the canonical one (`realai/core/world_model.py`) and archive the copies (GO). *Acceptance:* `benchmarks/bench_world_model.py` is unchanged.

## 5. Background tasks, routines and triggers

**Current state:** `/v1/tasks` in `v3_orchestrator.py` and `apps/api/routes/tasks.py`, `realai/memory/workflows/memory_summarizer_cron.yml`, `realai/hive_tools/tool_loop.py`, `realai/core/self_heal.py`. There is no scheduler module on main.

**Target:** `realai/core/tasks/`, a single local task queue (sqlite) with three kinds: one-off task, routine (cron-like), and trigger (event: file change, hive event, CI result). Every task runs an ability through the registry, so permissions apply automatically. Approval tasks park as `awaiting_approval`.

**Phases**
- **5a** Queue plus worker behind the existing `/v1/tasks`. *Acceptance:* create/list/cancel tests, and the worker survives a restart.
- **5b** Routines. *Acceptance:* a routine fires at a fake clock time.
- **5c** Triggers. *Acceptance:* a fake event enqueues exactly one task. An approval-level ability parks and never runs unapproved.

## 6. One /v1 API and one SDK

**Current state:** two servers expose /v1: `realai/orchestration/v3_orchestrator.py` (full surface) and `apps/api/routes/{chat,audio,embeddings,models,tasks,voice_ws}.py`, plus `realai/server/legacy_api.py`. There are also `realai/mcp/mcp_server.py` and `realai/mcp_server.py`. SDKs: `packages/realai-sdk/src/{client,types,providers}.ts`, `packages/sdk-ts/src/{index,envChatClient,registryClient}.ts` (#211 lint), `realai/packages/sdk-ts/src/*` (dup), `packages/sdk-py`, `realai/sdk-py`. Clients: `apps/vscode` (`src/consolePanel.ts`), `apps/dashboard`, `realai/voice_service/`, `realai/widget/`, and the console (`console.html`, `src/components/console/*`).

**Target:** one /v1 contract (OpenAPI generated from the core) and one `packages/sdk` with `chat`, `abilities`, `approvals` and `tasks` modules. Console, VS Code, voice and widget all show the same chat, approvals and task list via the SDK. **The console UI and voice trainer UI are not modified in this work.** They adopt the SDK only in a later, separately approved PR.

**Phases**
- **6a** OpenAPI snapshot test of the core's /v1. *Acceptance:* the snapshot is committed, and CI fails on drift.
- **6b** `packages/sdk` merging `realai-sdk` and `sdk-ts` (non-game parts), with the old names re-exporting. *Acceptance:* the SDK unit tests hit a stub server, and #211 lint stays at 0 errors.
- **6c** `apps/api` routes become thin proxies to the core, with no second implementation. *Acceptance:* a contract test runs the same requests against both and compares.
- **6d** `/v1/approvals` and the task list are exposed for clients. *Acceptance:* the SDK can list and approve; Security review.
- **6e** VS Code and widget adopt the SDK (separate PRs). Console and voice wait for travis's GO.
- **Archive:** `realai/packages/sdk-ts/*` and `realai/sdk-py` (dups); `packages/sdk-ts/src/*.js` game files duplicate `packages/sdk-ts/src/game/*` (see "What this is NOT").

## 7. Catalog evals in CI

**Current state:** `.github/workflows/ci.yml` runs `python -m pytest -q` and `pnpm run test`; `.github/workflows/codeql.yml` (`realai/.github/workflows/*` are dups to archive).

**Target:** `tests/catalog_evals/`, with one eval case per LIVE ability (input, expected shape, permission). CI step: `python -m pytest tests/catalog_evals -q`. A LIVE status without a passing eval fails CI.

**Phases**
- **7a** Eval runner plus cases for the 4 abilities in #213-216. *Acceptance:* green in CI.
- **7b** Cover every LIVE entry. *Acceptance:* a coverage check reports 100% of LIVE.
- **7c** Gate: a status change to LIVE requires an eval. A temporary status `LIVE-pending-eval` is allowed while the first evals are written: it fails the eval-coverage check but blocks no other work (other PRs and phases proceed). *Acceptance:* a negative test PR fails; a `LIVE-pending-eval` entry shows as a coverage failure only.

---

## Parallel work (not blocked by this plan)

- **#210** workspace tools / approval hardening: with Security for the final check. It is the base for §3.
- **#213-216** PR triage, vuln triage, CI failure classifier, tool router: open. Each changes the README LIVE count line (expect one-line rebases; ends at 68/78).
- **PARTIAL-to-LIVE plan:** `C:\Users\tsmit\agent-stage\partial_to_live_plan.md` (local-only, not in repo) (chess, synthetic organs, git-learn, CLI bridge, self-evolving, image gen and analysis). Video generation and the training pipeline stay PARTIAL.
- **Known local-only test failures:** 13 tests in `tests/unified/*` and `test_codeql_hardening` fail only in full local runs on travis's PC (test order). They pass in isolation and in CI. Phases 1b and 4a must not "fix" them by moving `modules/`.

## Risks

1. **Shim breakage:** many modules `import *` from old paths. Mitigation: keep shims and add the import-graph test before any archive.
2. **Hidden unique logic in duplicates:** diff each file before archiving and record the sha256.
3. **Permission regression:** routing everything through one gate can block real workflows. Mitigation: an allow-list with Security review, and fail closed.
4. **Two servers drifting:** the OpenAPI snapshot test (6a).
5. **Memory migration data loss:** read-only facade first, with a backup before any DB merge.
6. **Port confusion (see warning at top):** the orchestrator and `api_server`/`legacy_api` both default to 8001. Set `PORT=8000` for the API server until phase 6c.
7. **PC vs CI differences:** the known test-order failures can mask real regressions. Compare CI and isolated runs.

## What this is NOT

- Not the games. `packages/sdk-ts/src/game/*`, quests and NPC files, and atomic-fizz are out of scope.
- Not a rewrite, and no new model. The default model is never switched.
- Not a trading change. `trading.live` stays false, and LustLink is excluded.
- Not a console UI or voice trainer UI change.
- Not training. No adapter goes LIVE without Q1∧Q4 plus GO, and weights never go in git.
- Not deletion. Archives only, to `D:\ARCHIVE`, hash-verified, with GO.

## Security review artifacts (phases 3b-3d, 6d)

Each Security review is scoped to these named artifacts:

- **3b:** the permissions `check(ability, action, args)` entry point in `realai/core/permissions`.
- **3c:** the network egress proxy (the only path for outbound requests).
- **3d:** the money path (wallet signing / payouts; always `approval`, `trading.live` locked false).
- **6d:** the `/v1/approvals` contract (request, list, approve, deny schema and auth).

## Open decisions for travis (all decided 2026-10-29; see Decisions below)

- **D1** Approve this plan and its phase order (1→2→3→7 first, then 4, 5, 6)?
- **D2** Archive batches: GO per batch, or one GO per section?
- **D3** Should `apps/api` be the long-term public server (proxying the core), or should the core serve /v1 directly and `apps/api` be archived?
- **D4** Journal: there's no journal module on main. Create one in `realai/core/memory`, or point to an existing store?
- **D5** Canonical memory store: `realai/memory/sqlite_memory.py`?
- **D6** SDK package name: `packages/sdk` (new), or keep `@realai/sdk` from `packages/realai-sdk`?
- **D7** When may the console and voice adopt the SDK (6e)?
- **D8** Network policy for §3c: local-only by default, with a per-ability allow-list?

## Decisions (travis, final, 2026-10-29) — DECIDED: travis confirmed D1-D8 as his final decisions to Chief at 6:12 AM PT on 2026-10-29.

All of D1-D8 below are **decided**; they supersede the open questions above.

- **D1 (DECIDED):** order 1 -> 2 -> 3 -> 7, then 4, 5, 6. Permission and eval work de-risks the rest.
- **D2 (DECIDED):** one GO per section, or per archive batch inside a section. No blanket GO.
- **D3 (DECIDED):** the core serves /v1 directly once the OpenAPI snapshot is stable; `apps/api` stays a thin proxy only while external deploys still need it. Avoid two long-lived implementations.
- **D4 (DECIDED):** no journal module yet (a minimal stub in the memory facade at most); add one only when a concrete ability needs it.
- **D5 (DECIDED):** `realai/memory/sqlite_memory.py` is the candidate, pending the 4a inventory confirming it is the most complete and least divergent.
- **D6 (DECIDED):** a new `packages/sdk` that re-exports the old names.
- **D7 (DECIDED):** console and voice adopt the SDK after 6e (VS Code and the widget first).
- **D8 (DECIDED):** local-only by default, explicit per-ability allowlist, fail closed.
