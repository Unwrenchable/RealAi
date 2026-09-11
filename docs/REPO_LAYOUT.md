# RealAI-clean repo layout (single-root contract)

**Servers / bats:** see [`RUN_SERVERS.md`](RUN_SERVERS.md) and `START_HERE.bat`.

## Canonical env

| Variable | Value | Meaning |
|----------|-------|---------|
| `REALAI_HOME` | `C:\RealAI-clean` | **Product home** (same as `start_all.bat`) |
| `REALAI_PRODUCT_ROOT` / `REALAI_WORKSPACE` | `C:\RealAI-clean` | Product tree |
| `REALAI_PACKAGE` | `C:\RealAI-clean\realai` | Python package dir only |
| `REALAI_AGENTS_PATH` | `...\realai\agents\agentx\agents.json` | Live Hive agent registry |
| `REALAI_MODELS_DIR` | `C:\models\checkpoints_lora` | GGUF + TTS checkpoints |
| Hive | `http://127.0.0.1:8001` | Orchestrator |
| Vulkan | `http://127.0.0.1:8080` | llama-server |
| **RealAI Voice Lab** | `http://127.0.0.1:8890` | Provider-level TTS/STT (**not Grok/xAI**) |

```bat
set REALAI_HOME=C:\RealAI-clean
cd /d C:\RealAI-clean
START_HERE.bat
REM or: start_all.bat / realai-stack
```

## One product, two roles for `realai/` — not a nested repo

| Path | Role |
|------|------|
| `C:\RealAI-clean\` | **Product home** — apps, abilities, agents, modules, scripts, docs, bats |
| `C:\RealAI-clean\realai\` | **Python package** — orchestrator, craft, voice, `python -m realai` |
| `C:\Users\tsmit\realai\` | **Old git clone** — reference only; do not day-drive |

`RealAI-clean\realai\` has **no** `.git`. It exists so `import realai` works.  
Duplicate folders under the package (`realai\apps`, `realai\abilities`, …) are mirrors/leftovers — **edit the product-root copies** (`abilities\`, `agents\`, `fusion-ui\`, …) and the package trees Hive actually loads (`realai\agents\…`).

Setting `REALAI_HOME` to the nested package is what made agents/abilities look “lost.”

## Operator surfaces

| Surface | Entry |
|---------|--------|
| CLI | `realai` / `realai-stack` / `realai-health` |
| VS Code Console | Extension `realai-vscode` → Open Console |
| Voice Lab API | `python -m realai.voice.lab_server` (port 8890) |
| Honesty map | `realai/ability_catalog.py` + `docs/ABILITY_ALIASES.md` |

## Import / archaeology

| Path | Use |
|------|-----|
| `scan_results/from_copilot_export/` | Curated blobs from Grok asset export (diff only) |
| `docs/sessions/UNIFY_FROM_COPILOT_EXPORTS.md` | Full unify narrative |
| `docs/sessions/PHASES.md` | Development phases |
