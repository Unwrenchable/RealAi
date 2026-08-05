# SUCCESS — RealAI deepen loop is live

**When:** 2026-07-15  
**Stack:** Vulkan :8080 (Qwen) · Orchestrator :8001 (`REALAI_SELF_IMPROVE=true`) · Chat OK · Hive OK

## What we were trying to reach

A **successful run** that is **repeatable**, and where **each run can go deeper** than the last (keywords, coverage, artifacts, hive reflection) — not one-off manual scans.

## Proven runs

| Run | Deeper? | Keywords | Score | Success |
|-----|---------|----------|-------|---------|
| 1 | **True** | 301 → **304** | 62.19 → 62.22 | True |
| 2 | False (plateau) | 304 → 304 | 62.22 → 62.22 | True |
| 3 (API) | **True** | 304 → **325** | 62.22 → 62.43 | True |

- Chat: **“hive live”** / **“RealAI deepen ready”**
- Multi-agent: **ok=true**, engine=`orchestration_gold`
- Deepen via **HTTP API**: `POST /v1/deepen`

## How every run goes deeper

`python -m realai.deepen_cycle` (or `POST /v1/deepen`):

1. **Mine gold** — recycle map, hive uniques, recovered packages → new keywords  
2. **Learn** — merge into `ability_keywords_learned.json` + refresh ability catalog  
3. **Assemble** — gold index / promote queue (when self-improve on)  
4. **Hive reflect** — planner→worker→critic on what got deeper (Vulkan)  
5. **Record** — `deepen_history.jsonl` so the next run knows prior depth  

Plateau runs still **succeed**; mining step re-opens depth when inventory is flat.

## Commands (always)

```bat
REM 1) Vulkan (if down)
cd C:\llama-vulkan
start /MIN llama-server.exe -m C:\realai\models\qwen2.5-coder-7b-instruct-q5_k_m.gguf --host 127.0.0.1 --port 8080 -c 4096 -ngl 99 --jinja

REM 2) Orchestrator
cd C:\realai
set REALAI_SELF_IMPROVE=true
set REALAI_VULKAN_BASE=http://127.0.0.1:8080
set REALAI_TRAINING_DATA=C:\realai\training\data
set REALAI_MEMORY_INJECT=true
python -m realai.v3_orchestrator --host 127.0.0.1 --port 8001

REM 3) Deepen (each run)
python -m realai.deepen_cycle
REM or:
curl -X POST http://127.0.0.1:8001/v1/deepen -H "Content-Type: application/json" -d "{\"assemble\":true,\"hive\":true}"

REM 4) Status
curl http://127.0.0.1:8001/v1/deepen/status
```

Or one bat: `start_v3_stack.bat` then deepen.

## Artifacts

| Path | Role |
|------|------|
| `realai/deepen_cycle.py` | Depth engine |
| `scan_results/deepen_history.jsonl` | Every run |
| `scan_results/deepen_last.md` | Latest human report |
| `GET /v1/deepen/status` | Last + history count |
| `POST /v1/deepen` | Trigger deepen |

## Bottom line

**We got there:** live GPU chat + self-improve + hive + a **durable deepen loop** that recorded **True → plateau → True** with keywords **301 → 304 → 325**.  
Run `python -m realai.deepen_cycle` anytime; it keeps digging.
