# RealAI Hive CLI

Professional, orchestrator-centric command line for the RealAI Hive.

Full command tree: [`cli/hive/CLI_TREE.md`](cli/hive/CLI_TREE.md)

```bat
python -m realai
realai status
realai stack up
realai route "refactor gpu resume"
realai run "verify hive pipeline"
realai agents --hive
realai ability run chat_completion --input "ping"
realai world show
realai gpu status
realai quarantine scan
```

## Entry points

| Command | Target |
|---------|--------|
| `realai` / `realai-cli` | `realai.cli.hive.app:main` |
| `python -m realai` | same |
| `realai-craft` | Craft REPL (compat) |

## Command map

| Group | Purpose |
|-------|---------|
| `(default)` / `status` / `doctor` | Hive dashboard |
| `stack` / `gpu` / `orch` / `vulkan` | Local GPU + orchestrator |
| `models` / `providers` | Model facade |
| `agents` / `multi` / `task` | Agent roster + multi-agent + tasks |
| `abilities` / `ability` / `tools` / `tool` | Catalog + execute |
| `heal` | Self-heal status/cycle/assemble/promote |
| `world` | World-model inspect (read-only) |
| `chat` / `ask` | Orchestrator chat (not Craft) |
| `craft` | Escape hatch to Craft |
| `quarantine` | Index `_quarantine` for unique/lost promote candidates |

## Quarantine (self-improve source)

`_quarantine` is a **learn/promote discovery root** (not a blind `dispatch all` peer):

```bat
realai quarantine scan
realai quarantine list --promote-only
realai quarantine find world_model
```

Dispatcher also resolves phase scripts under `_quarantine` and runs `quarantine_catalog.py` on quarantine/learn keywords.

## Paths

- Vulkan: `C:\llama-vulkan\llama-server.exe`
- Weights: `C:\models\checkpoints_lora`
- API: `http://127.0.0.1:8001` (`REALAI_API_BASE`)

## Notes

- Default (no args) is a **status dashboard**, not a chat REPL.
- Craft is secondary: `realai craft`.
- After LoRA train pauses Vulkan for VRAM: `realai gpu resume` or `realai stack up`.
