# Grok session map (RealAI development phases)

Grok stores sessions under `~/.grok/sessions/<url-encoded-cwd>/`.  
**Do not move those folders** — `/resume` and the dashboard depend on that layout.

This directory is the **readable index** so agents can see which sessions are RealAI product work, which phases they belong to, and which roots are unrelated.

| File | Purpose |
|------|---------|
| [`PHASES.md`](PHASES.md) | Development-phase timeline (start here) |
| [`LANES.md`](LANES.md) | Which session roots are RealAI vs not |
| [`UNIFY_FROM_COPILOT_EXPORTS.md`](UNIFY_FROM_COPILOT_EXPORTS.md) | Copilot dump + asset export → living abilities/tools unify map |
| [`../ABILITY_ALIASES.md`](../ABILITY_ALIASES.md) | Historical ability names → living tools |
| [`../REPO_LAYOUT.md`](../REPO_LAYOUT.md) | Single-root `REALAI_HOME` + Voice Lab ports |
| [`catalog.json`](catalog.json) | Machine-readable inventory of Grok sessions |
| [`copilot_asset_index.jsonl`](copilot_asset_index.jsonl) | Scored blobs from prod-mc-asset-server export |
| [`live_tools.txt`](live_tools.txt) | Live Hive tool names snapshot |
| [`refresh_catalog.ps1`](refresh_catalog.ps1) | Rebuild `catalog.json` from live `summary.json` files |

## Quick rule for agents

1. Read **PHASES.md** for “where we are / what happened”.
2. Use **catalog.json** to find the session id + absolute `session_dir`.
3. Open that session’s `summary.json` / `last_recap` / `updates.jsonl` only when you need detail.
4. Ignore lanes tagged `unrelated` or empty stub sessions (`num_chat_messages <= 2`, no title).

## Current product home

- Living product tree: `C:\RealAI-clean`
- Primary session root: `C:\Users\tsmit\.grok\sessions\C%3A%5CRealAI-clean`
- Legacy mega-repo sessions: `C:\Users\tsmit\.grok\sessions\C%3A%5Crealai` (historical only)
