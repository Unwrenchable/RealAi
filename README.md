# RealAI

RealAI is a local-first AI hive. It is an orchestrator (`realai/v3_orchestrator.py`, port `8001`) plus local GGUF models served by `llama-server` on Vulkan (port `8080`). On top of that it does multi-agent work, runs tools, has a console UI and a VS Code extension (`apps/vscode/`), and exposes an OpenAI-compatible API (`python -m realai.api_server`).

> **Trust `realai/ability_catalog.py` / `ABILITIES.md` over any feature list; status LIVE/PARTIAL/STUB.**
> The catalog is the source of truth. If this README and the catalog disagree, the catalog wins.
> (`ABILITIES.md` and the browser console currently live on the
> [`live/realai-clean-20260911`](https://github.com/Unwrenchable/RealAi/tree/live/realai-clean-20260911) branch.)

## What works today

Only abilities the catalog marks **LIVE**:

| Ability (catalog id) | How to reach it |
|---|---|
| Chat completion (`chat_completion`) | `POST /v1/chat/completions` |
| Text generation (`text_generation`) | `POST /v1/chat/completions` |
| Code generation (`code_generation`) | `POST /v1/chat/completions` |
| Embeddings (`embeddings`) | `POST /v1/embeddings` |
| Local inference, Vulkan / GGUF (`local_inference`) | `http://127.0.0.1:8080`, via the orchestrator |
| Kilo-era gold recovery wiring (`kilo_recovery`) | `GET /v1/recovery` |
| Next.js operator UI (`frontend_ui`) | `http://127.0.0.1:3000` |

## Quick local start (Windows + Vulkan)

Tested on Windows with an AMD RX 6700 XT. Cross-platform support (Linux/macOS, CUDA/Metal) is planned.

```powershell
# 1) Vulkan model server (7B GGUF)
#    -fa off is required on the RX 6700 XT: flash attention gives garbled output ("??????") there.
C:\llama-vulkan\llama-server.exe `
  -m "C:\realai\models\qwen2.5-coder-7b-instruct-q5_k_m.gguf" `
  --host 127.0.0.1 --port 8080 -ngl 99 -c 16384 -fa off --jinja

# 2) Orchestrator (hive gateway)
$env:REALAI_VULKAN_BASE = "http://127.0.0.1:8080"
python -m realai.v3_orchestrator --host 127.0.0.1 --port 8001
```

Or use `scripts/start_v3_stack.ps1`, which starts both. Check `-fa off` is in its llama-server arguments before using it on an RX 6700 XT.

Keep both servers bound to `127.0.0.1` unless you know you need LAN access.

## Where to look

- **Ability status:** [`realai/ability_catalog.py`](realai/ability_catalog.py) (and `ABILITIES.md` on the live branch)
- **Architecture:** [`docs/architecture.md`](docs/architecture.md) here, and `ARCHITECTURE.md` on the live branch
- **Local setup detail:** [`QUICKSTART_LOCAL.md`](QUICKSTART_LOCAL.md), [`QUICKSTART.md`](QUICKSTART.md)

## Partial and stub abilities

These exist in some form but are not finished. Do not rely on them yet.

- **PARTIAL:** code execution (`code_execution`), task automation (`task_automation`), memory and learning (`memory_learning`), self-reflection (`self_reflection`), knowledge synthesis (`knowledge_synthesis`), multi-agent orchestration (`multi_agent`), observability and self-improvement (`observability_self_improve`), training pipeline (`training_pipeline`).
- **STUB:** image generation (`image_generation`), video generation (`video_generation`), audio transcription (`audio_transcription`), audio speech (`audio_speech`).

Everything else in the catalog is CODE, SOFT, GOLD or MISSING: present as code or recovered material only, not a working feature.

## Install

```bash
git clone https://github.com/Unwrenchable/RealAi.git
cd RealAi
pip install -r requirements.txt
```

`pip install -e .` does not work on `main` yet: `setup.py` lists a package directory that is missing (`realai-core/agent_tools/agents_impl`). Run from the repo root instead.

You also need a `llama-server` build with Vulkan and a GGUF model for local inference.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). When you add or change an ability, update its status in `realai/ability_catalog.py` in the same PR.

## License

MIT. See [`LICENSE`](LICENSE).
