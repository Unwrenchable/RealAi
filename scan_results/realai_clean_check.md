# realai-clean check (2026-07-16)

Path: `C:\\Users\\tsmit\\realai-clean`

## Status
- **Exists**: yes — full RealAI tree (api_server, aura, realai/, agent-tools, apps, archive, …)
- Already in `era_map.json` as secondary gold + external ability root
- **Now also** in self-heal desktop/clean/local discover scanner roots

## Self-heal
```json
POST /v1/self-heal/discover
{"mode": "clean"}
```
Also included when mode is `desktop`, `local`, or `all`.

## Staged
`recovered/from_realai_clean/`

## Note
P0 ghost basenames (self_*_tool.py, aura_memory.py, world_model.json) still unlikely here;
core gold is standard package layout (world_model.py, aura/memory.py, agent_runtime.py, …).
