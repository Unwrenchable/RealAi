# Auth for `POST /v1/tools/execute`

The route lives in `realai/orchestration/v3_orchestrator.py` (`Handler.do_POST`, the hive / v3 orchestrator on `:8001`).
`realai/orchestration/v3_runtime_bridge.py` does not reference the route.
`modules/orchestrators/nested_realai_v3_orchestrator.py` and `realai/orchestrators/nested_realai_v3_orchestrator.py` are older copies that serve their own `/v1/tools/execute`; they are **not** gated by this change (follow-up).
`realai/server/unified_routes.py` has its own audited envelope for the same path, which does not run tools, so it is not gated here.

The gate is `realai/orchestration/tool_auth.py`. It is **off by default on a loopback bind**. It is **forced on** (fail closed) when `REALAI_ENV=production` or the orchestrator binds a non-loopback host; in that case the orchestrator refuses to start unless `REALAI_TOOLS_TOKEN` is set.

## Settings

| Env var | Default | Meaning |
|---|---|---|
| `REALAI_TOOLS_AUTH` | off | `1`/`true`/`yes`/`on` turns the gate on |
| `REALAI_TOOLS_TOKEN` | unset | Shared secret. Callers send `Authorization: Bearer <token>`. Compared with `hmac.compare_digest`. Never logged. |
| `REALAI_TOOLS_ALLOW` | unset (default allowlist = read-only core tools only) | Comma-separated extra tool names, added to the read-only core set. No other tool (e.g. `realai_cli_bridge`, image/video generation, `self_evolving`, `training_pipeline`, `learn_git`) is allowed unless listed here. |
| `REALAI_ENV` | unset | `production` forces the gate on |
| `REALAI_TOOLS_RATE` / `REALAI_TOOLS_RATE_WINDOW` | 60 / 60 s | Per-client (by remote IP) fixed-window limit; unauthenticated calls use a separate pre-auth bucket; at most 4096 tracked clients (oldest evicted) |

Responses when the gate is on:

* `400 bad_request`: tool name is not a string.
* `503 unavailable`: gate on but no token set (fail closed).
* `429 rate_limited`: client over the limit.
* `401 unauthorized`: missing, malformed or wrong bearer token.
* `403 forbidden`: tool not on the allowlist. (401/403/503 bodies are generic.)

Every call writes one line to the `realai.tools_audit` logger:
`tools_execute ability=<name> result=<code_reason> client=<ip>`. Name and client are stripped to `[A-Za-z0-9._:-]` and capped (120 / 64 chars) to stop log injection. No token, no arguments, no results.

Default read-only core tools: `list_agents`, `agent_tools_assess`, `ability.pr_triage`, `ability.vuln_triage`,
`ability.ci_failure_classify`, `ability.coach`, `rackup_invoke`. Anything else (for example `aura_memory`,
`hive_run`, `multi_agent_run`, `self_heal_*`) must be added through `REALAI_TOOLS_ALLOW`.

**Bind host:** the orchestrator already takes `--host` / `HOST` and defaults to `127.0.0.1`. Keep it on `127.0.0.1`.
Binding anything else forces the gate on and requires `REALAI_TOOLS_TOKEN` at startup.

## Caller list (Step A, 2026-10-29)

Searched `C:\RealAI-clean`, `C:\tools\realai`, `C:\Users\tsmit\realai_unified_api` and every git repo directly under
`C:\Users\tsmit` for `tools/execute`. Docs, catalogs and training data that only mention the path are left out.

| Caller | File | Host / port | Tools it calls | Sends token today? |
|---|---|---|---|---|
| RackUp backend coach (game) | `Rack_em_up/rackup-backend/src/ai/realai-coach.client.ts`, `realai-endpoint.ts` | `REALAI_BASE_URL`, default `http://127.0.0.1:8001` | `rackup_invoke` / coach | No |
| RackUp smoke tests | `Rack_em_up/rackup-backend/test/smoke/brackets-chips-coach.smoke.spec.ts` | same | coach | No |
| `realai` CLI provider | `C:\tools\realai\core\provider.js` (`http.post('/tools/execute')`) | hive base, `http://127.0.0.1:8001/v1` | any tool, `aura_memory` | No |
| `realai` CLI hive brain | `C:\tools\realai\core\hive-brain.js` | `127.0.0.1:8001` | `aura_memory` (remember/recall), planned tools | No |
| `realai` CLI commands | `C:\tools\realai\commands\hive.js`, `ability.js`, `do.js` | `127.0.0.1:8001` | user-chosen tool | No |
| `realai` CLI tests | `C:\tools\realai\test\t-hive-link.js`, `mock-hive.js`, `mock-server.js` | mock server | n/a | n/a |
| MCP server | `realai/mcp_server.py` (`_hive_request`) | hive URL, `127.0.0.1:8001` | any tool | No |
| Hive CLI client | `realai/cli/hive/client.py` | hive URL | any tool | No |
| VS Code extension | `apps/vscode/src/realaiClient.ts` | configured base URL | any tool | No |
| Console UI | `console.html`, `apps/vscode/webview/console.html` | same origin `:8001` | any tool | No |
| Self-heal probe | `realai/core/self_heal.py`, `realai/scripts/self_heal.py` | `127.0.0.1:8001` | `list_agents` | No |
| Live gap agent | `scripts/live_gap_agent.py`, `realai/scripts/live_gap_agent.py` | `127.0.0.1:8001` | `list_agents` | No |
| Daily smoke | `scripts/daily_smoke.ps1` | `http://127.0.0.1:8001` | `rackup_invoke` / `ability.coach` | No |
| Matrix verifiers | `scripts/verify_v3_matrix.py` (+ copies in `benchmarks/`, `scanners/`, `realai/benchmarks/`, `realai/scripts/`) | `127.0.0.1:8001` | assorted | No |
| Smoke all abilities | `scripts/_smoke_all_abilities_tools_agents.py` | `127.0.0.1:8001` | every ability | No |
| Atomic Fizz hive client | `abilities/atomic_fizz_hive_client.py` | hive URL | ability calls | No |
| Launcher / dashboard | `C:\Users\tsmit\realai_unified_api` | only in logs and `_review` docs; no direct caller found | n/a | n/a |

No caller sends a bearer token yet. Turning the flag on breaks every row above until that caller sends
`Authorization: Bearer $REALAI_TOOLS_TOKEN` and its tools are on the allowlist. Roll out caller by caller, then flip the flag.

## Workspace tools (B3 piece 1)

`workspace_list`, `workspace_read` and `workspace_grep` are in the default allowlist. They are confined to the workspace root (`REALAI_TOOLS_WORKSPACE_ROOT`, else the craft project workspace): absolute, drive, UNC and `..` paths are refused, and any symlink or junction on the path is refused. Caps: read 1 MB per file and 200 lines per call, list 200 entries, grep 2000 files / 40 hits / 1 MB per file, literal patterns up to 200 chars.

`workspace_write` is off by default. It runs only when `workspace_write` is listed in `REALAI_TOOLS_ALLOW` (and over HTTP it still goes through the approval gate). Writes are capped at 256 KB and opened with O_NOFOLLOW where the OS has it.

