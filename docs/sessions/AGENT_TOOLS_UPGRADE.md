# Agent-tools → RealAI upgrade

Pulled from:

- `C:\Users\tsmit\agent_tools_`
- `C:\Users\tsmit\agent-tools-main\agent-tools-main`
- recon notes in `C:\Users\tsmit\agent-tools` (hash/inventory only)

## Merged into RealAI

- **+40 agents** into Hive registry `realai/agents/agentx/agents.json` (68 → **108**)
- Product mirror `agents/agentx/agents.json` also merged (**119**)
- **Access profiles** `safe` / `balanced` / `power`
- **Runtime packs**: `.agentx` + `.agent.json` (architect, coder, overmind, security, …)
- **Workflows**: `agents/workflows/workflow-feature-dev.json`, `workflow-security-review.json`

## Agent Activity UI (was AgentX `:7070` dashboard)

Now Hive-served at **http://127.0.0.1:8001/agents-ui/**

- Force-directed agent graph + live SSE feed
- RealAI Fusion theme
- Run dock → `POST /v1/agents/run` (Hive multi-agent)
- Sim toggle → `POST /v1/agents/simulation`
- APIs: `/v1/agents?full=1`, `/v1/agents/graph`, `/v1/agents/profiles`, `/v1/agents/events`, `/v1/agents/executions`

Supporting module: `realai/agent_activity.py`

## Agency-agents import (`C:\tmp\agency-agents`)

- Parsed **142** category agents (skipped strategy/examples/docs noise)
- Hive registry **108 → 218** (+110 new, 32 enriched)
- Markdown personas copied to `agents/agency/`
- Snapshot: `agents/agentx/agency_import.json`
- Extra workflows: book-chapter, landing-page, startup-mvp, with-memory
- Re-run: `python scripts/import_agency_agents_into_realai.py`
