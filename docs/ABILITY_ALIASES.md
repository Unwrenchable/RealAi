# Ability / command aliases (Copilot history → living RealAI)

Copilot/Grok chats named many `ability.*` / `/exec` commands that are **not** registry IDs.
Use this map so Console, Craft, and docs speak one language.

| Alias (historical) | Living surface | Status |
|--------------------|----------------|--------|
| `ability.walk_root` / `/walk` | workspace tools + scanners (`workspace_list/grep`, scan scripts) | SOFT → use tools |
| `ability.organize_repo` | `scripts/` reorg + quarantine flows | SOFT |
| `ability.deep_unify_walk` | scanners / deep nests under `scan_results/` | SOFT |
| `ability.promote` / `curated_promote` | `scripts/curated_promote.py`, self-heal promote queue | LIVE (script) |
| `ability.deep_promote_scan` / `deep_promote_wire` | `abilities/deep_promote.py` + tool `ability.deep_promote` | LIVE |
| `ability.self_heal` / `self_heal_loop` / `self_heal_cycle` | `self_heal_status`, `self_heal_assemble`, `self_heal_promote_dry` | LIVE |
| `ability.self_heal_promote` | self-heal promote queue / dry tools | LIVE |
| `ability.plugin_discover` / `plugin_merge` / `plugin_promote` | `ability.plugin_system`, `plugins_surface` | PARTIAL |
| `ability.plugin_registry_build` | `plugins/` registry builders | PARTIAL |
| `ability.world_model_ingest` / `expand` / `merge` / `promote` | `world_brain` tool + world model modules | PARTIAL |
| Invented `/exec walker.scan` etc. | **Rejected** — failed live_exec; do not reintroduce | MISSING |

## Operator cheatsheet (verified)

```text
/tools  /hive  /heal  /lora  /agents  /coverage
/multi <task>
/phase  /patches  /repo     (VS Code Console deterministic)
POST /v1/tools/execute
POST /v1/abilities/run
POST /v1/multi-agent/run
```

## Voice (RealAI provider — not Grok)

| Item | Value |
|------|--------|
| Provider id | `realai-voice` |
| Lab API | `http://127.0.0.1:8890` |
| Start | `realai\voice\start_voice_lab.bat` |
| Weights | `C:\models\checkpoints_lora` (Kokoro / Fish / XTTS) |
| Hive tools | `voice_health`, `voice_inventory`, `voice_speak`, `voice_listen` |

No xAI / Grok cloud TTS on this path.
