# Approval gate for write / exec tools (decision 5, 2026-10-16)

Module: `realai/core/approval_gate.py`. Hive tool: `request_approval` (`realai/hive_tools/approvals.py`).

## Flow
1. **Request.** A model, agent or the hive calls a write/exec tool. Calling `search_replace`, `run_command`/`run_terminal_command`, `run_script`, `write_file`, `auto_wire`, `self_heal_promote*`, `self_extend` or `self_repair` through `v3_orchestrator._run_tool`, or `request_approval` in the hive tool loop, does not execute anything. The gate:
   - validates the request,
   - builds a **dry-run preview**: a unified diff, or the exact argv plus cwd and timeout, or a static plan of what the tool writes,
   - stores a `pending` item in the existing approvals store (`.approvals.json`, the format `approval_store` uses: `{"items":[{"id","action":"gate:<action>","payload","status"}]}`),
   - returns `{"status":"pending","approval_id":"apr-…","preview":…,"executed":false}`.
2. **Approve.** A human approves in the approval UI (`status` → `approved`). The alternative is `python -m realai.core.approval_gate approve <id>`, which shows the diff or command and requires typing the id.
3. **Execute.** Run `python -m realai.core.approval_gate execute <id>`, or call the same tool again with `approval_id=<id>`. It runs only if the item is `approved`, belongs to the same action, its preview hash still matches, and the file is unchanged since the request (otherwise it reports `stale`). The request then becomes `executed`, so it cannot run twice.

## Guarantees
- **Deny by default.** Anything not approved is refused. The model-supplied `approved=True` shortcut in `realai/core/tools/hive_executor.py` is now ignored unless `REALAI_APPROVAL_TRUST_FLAG=1`, because the model could set it itself. An approval for one tool/action never unlocks another.
- **Workspace-scoped.** The workspace is `REALAI_WORKSPACE`, then `REALAI_HOME`, then cwd. Paths outside it are refused, and so are protected paths: `.git/`, `.env*`, `keys/`, `secrets/`, `wallets/`, `.ssh/`, `*.pem`/`*.key`, the approvals store and its audit log. Commands that mention the approvals store are refused.
- **Audit log.** Every request, refusal, approval, rejection and execution is appended to `<store>.audit.jsonl`, or to `REALAI_APPROVALS_AUDIT` if set.
- **Money stays separately locked.** Sends, transfers, payouts, wallet signing, keys and seed phrases are refused at request time, and again at execution. This gate never provides a money path.
- **self_data.** Training sees only `request_approval`. It has no approve or execute tool. Offline (self_data, spotcheck, verify) it writes to a private temp store, never the real queue. The verifier (`recompute_check`) rejects any row whose result is not `pending`/`refused` or has `executed: true`. Spotcheck extended adds `approval_command` and `approval_money_refuse`.
- **Escape hatch.** `REALAI_EXEC_UNGATED=1` (default **off**) restores the old ungated `_run_tool` behaviour for Travis's own console sessions. User-typed explicit live-exec in chat (`realai.bot.live_exec.try_live_exec`) is human-initiated and unchanged.

## Store path
The gate uses `REALAI_APPROVALS_STORE`, then `APPROVALS_STORE`, then `<workspace>/.approvals.json`. This matches the `approval_status` tool. The Flask approval UI (`approval_store`) reads `APPROVALS_STORE`, falling back to cwd `.approvals.json`. Set `APPROVALS_STORE` once so the UI, the gate and `approval_status` all share one file.
