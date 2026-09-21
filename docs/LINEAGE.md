# Lineage — v1 and v2 live inside v3

RealAI is one intelligence. Versions are expansions, not replacements.

## Rule

Do not recreate `v1/`, `v2/`, `RealAIProject/`, `realai_sdk/`, or `og_mess/` on live.
Promote unique **modules** into the live package names below.

## v1 — provider + surfaces

Implemented in live when you use:

- OpenAI-compatible API — `realai/server`, `realai/api_server.py`, `apps/api`
- Local models / Vulkan — `realai/core/local_models.py`, `realai/model_assets.py`
- Frontend + VS Code — `frontend/`, `apps/vscode/`
- Config — `realai.toml`, `models.yaml`, `providers.yaml`

Still parked (promote only if gold loses):

- `local/desktop-realai-sdk-js-202604`
- `recovery/github-clone/...` realai-core UI clients

## v2 — agents, plugins, self-* , training, organs

Implemented in live when you use:

- Agent tools / sandbox — `realai/agent_tools_gold`, `agent_tools`
- Plugin host + RackUp — `realai/plugins`, `realai/plugins/rackup_coach`
- Self-heal / improve / build — `realai/self_heal.py`, `realai/core/self_builder.py`, `realai/core/self_improvement.py`, `realai/core/closed_loop.py`
- Organs — `modules/organs`
- Training / LoRA — `realai/plugins/train_qwen_lora_directml.py`, `realai/training`, `modules/training`
- Design system — `packages/design-system`

Still parked:

- `recovery/desktop-*` unique desktop agents / CLI
- `recovery/unique-modules/.../gold/from_desktop_*`
- JS commands under `C:\\tools\\realai` cited by the catalog `gold_paths`

## v3 — hive operator

Implemented in live when you use:

- `python -m realai.v3_orchestrator`
- `realai.orchestration.v3_runtime_bridge`
- Ability catalog + `/v1/capabilities`
- Craft / console / slash tools

v3 does not delete v1 or v2. It **calls** them.

## Wiring check (definition of "implemented")

A v1/v2 module is implemented in live only if:

1. A stable import exists (`realai.*` or `modules.*` or `abilities.*`).
2. Hive or CLI can reach it (`/v1/tools`, `/v1/abilities`, or `realai` CLI).
3. The catalog row points at an in-repo path, not only `C:\\tools\\realai`.

If (3) fails, status is PARTIAL even if a Python wrapper exists.
