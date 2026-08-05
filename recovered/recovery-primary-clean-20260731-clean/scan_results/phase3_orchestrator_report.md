# Phase 3 — Training + Self-Improve on Live v3 Stack

## Architecture

```
Next UI :3000
    │  REALAI_API_BASE=http://127.0.0.1:8001
    ▼
v3 Orchestrator :8001   (realai.v3_orchestrator)
    │  chat proxy + operator system prompt
    │  /v1/training/*  /v1/self-improve/*
    ▼
AMD Vulkan llama-server :8080  (Qwen GGUF, -ngl 99)
```

## What was wired

| Component | Path / endpoint |
|-----------|-----------------|
| Orchestrator | `realai/v3_orchestrator.py` |
| Stack starter | `start_v3_stack.bat` |
| Training plan | `realai/training/finetune.py` → `training/data/` |
| UI env | `.env.local` → `:8001` |
| UI routes | `/api/training/status`, `/api/self-improve/status` |

## Smoke tests (pass)

| Check | Result |
|-------|--------|
| `GET :8001/health` | ok + vulkan ok |
| `POST :8001/v1/chat/completions` | 200 `"phase3 wired"` |
| `GET :8001/v1/training/status` | dataset + manifests present |
| `GET :8001/v1/training/plan` | status ready |
| `POST :8001/v1/self-improve/evaluate` | ok, overall 0.8, training_ready 1.0 |

## How to start later

```bat
C:\realai\start_v3_stack.bat
REM then Next UI:
cd C:\Users\tsmit\realai\apps\frontend
node_modules\.bin\next.cmd dev -p 3000 -H 127.0.0.1
```

Open: **http://127.0.0.1:3000**

## Env

```
REALAI_VULKAN_BASE=http://127.0.0.1:8080
REALAI_SELF_IMPROVE=true
REALAI_TRAINING_DATA=C:\realai\training\data
REALAI_API_BASE=http://127.0.0.1:8001
```

## Notes

- Self-improve remains gated; orchestrator started with flag on.
- Chat still runs on Vulkan GPU (fast path).
- Full GGUF retrain still manual (plan steps list export → register → restart server).
