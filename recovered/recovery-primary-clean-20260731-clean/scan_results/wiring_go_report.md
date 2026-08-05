# Wiring go — agent_tools + multi-agent on live path

## Delivered

| Feature | Endpoint / usage | Status |
|---------|------------------|--------|
| Tool catalog | `GET /v1/tools` | **LIVE** (10 tools) |
| agent_tools status | `GET /v1/agent-tools/status` | **LIVE** (68 agents, 3 packages) |
| agent_tools list/search | `POST /v1/tools/execute` `agent_tools_list_agents` | **LIVE** |
| Access profiles | `agent_tools_list_profiles` / `agent_tools_assess` | **LIVE** (informational) |
| Ability coverage tool | `ability_coverage` | **LIVE** |
| Multi-agent pipeline | `POST /v1/multi-agent/run` | **LIVE** (`orchestration_gold` + Vulkan) |
| Chat multi-agent | `POST /v1/chat/completions` `{"multi_agent": true}` | **LIVE** |
| Verify matrix | | **31/31 PASS** |

## Read-only safety

- No write tools, no network tools, no unattended promote apply from tool surface
- Self-heal assemble/promote still gated on `REALAI_SELF_IMPROVE=true`

## Still partial / missing

- `engine/` `providers/` `tooling/` under agent_tools remain SOURCES placeholders (no full source in GitHub core package)
- Historical Python 3.14 `.pyc` still not decompiled on 3.12
- Multi-agent quality depends on local model; not full hive task-graph
- Current orch process may need env restart for `REALAI_SELF_IMPROVE=true` if evaluate/mutations required

## Example calls

```bash
curl http://127.0.0.1:8001/v1/tools
curl http://127.0.0.1:8001/v1/agent-tools/status

curl -X POST http://127.0.0.1:8001/v1/tools/execute \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"agent_tools_list_agents\",\"arguments\":{\"query\":\"documentation\",\"limit\":5}}"

curl -X POST http://127.0.0.1:8001/v1/multi-agent/run \
  -H "Content-Type: application/json" \
  -d "{\"task\":\"Summarize RealAI self-heal loop\",\"mode\":\"pipeline\",\"max_tokens\":256}"

curl -X POST http://127.0.0.1:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d "{\"multi_agent\":true,\"messages\":[{\"role\":\"user\",\"content\":\"Plan a safe promote\"}],\"max_tokens\":256}"
```

## Files

- `realai/v3_runtime_bridge.py` — bridge
- `realai/v3_orchestrator.py` — wired endpoints
- `realai/agent_tools_gold/` + `data/` — recovered package + agentx registry data
