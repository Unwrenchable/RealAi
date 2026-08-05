# AgentX Pack for realai

This repository uses the [agent-tools](https://github.com/Unwrenchable/agent-tools) registry format.

## Included
- `agents.json`: 78 agents — realai-specific pilots + enriched core agents from agent-tools
- `access_profiles.json`: safe / balanced / power profiles
- `agency_import.json`: imported agents from agency-agents

## realai-specific pilots

| Agent ID | Role | Profile |
|---|---|---|
| `realai-fullstack-dev` | Full-Stack Developer (realai.py, api_server.py, GUI) | balanced |
| `realai-capability-dev` | Capability Developer (stub → real implementations) | balanced |
| `realai-provider-specialist` | Provider Integration (9 AI providers) | balanced |
| `realai-implementation-pilot` | Scoped code changes with test validation | balanced |
| `realai-documentation-pilot` | README, API.md, QUICKSTART, docstrings | balanced |
| `realai-qa-pilot` | test_realai.py coverage and CI gates | balanced |
| `realai-security-hardener` | OWASP, CVE triage, secrets hygiene | balanced |
| `realai-orchestrator` | Multi-agent workflow coordination | power |
| `realai-repo-architect` | Architecture consistency and upgrade planning | safe |

## Suggested commands
```bash
# List all agents
agentx list

# Find realai-specific agents
agentx find realai

# Validate agent access
agentx check realai-fullstack-dev --profile balanced
agentx check realai-capability-dev --profile balanced
agentx check realai-orchestrator --profile power

# Recommend narrowest profile
agentx recommend realai-security-hardener
```
