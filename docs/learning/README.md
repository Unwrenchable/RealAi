# Git-learn packets

Offline, static pipeline: scan a git tree → learning packet → optional coach plugin stub.

| Entry | Starts heal / GPU / orch? |
|-------|---------------------------|
| `python -m realai.learn_git <path-or-url> [--write]` | **No** |
| Craft `/learn <path-or-url> [--write]` | **No** |
| Hive `realai learn <path-or-url> [--write]` | **No** |

Packets land in `realai/catalog/learned/<slug>/packet.json` (canonical) and a copy at `docs/learning/<slug>.json`.

Plugin stubs (only with `--write`) mirror `atomicfizz_coach` / `rackup_coach`:

`realai/plugins/<slug>_coach/` — `manifest.yaml` + `invoke` + stub abilities.

Clone cache: `realai/.learn_cache/` (gitignored, disposable).
