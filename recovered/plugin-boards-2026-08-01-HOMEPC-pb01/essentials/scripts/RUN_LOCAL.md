# RealAI — fully local run + self-heal loops

## One command (recommended)

Open **PowerShell** (Windows):

```powershell
powershell -ExecutionPolicy Bypass -File C:\realai\scripts\run_local_selfheal.ps1
```

Or double-click:

```text
C:\realai\scripts\run_local_selfheal.bat
```

That will:

1. Start **Vulkan llama-server** on `:8080` (Qwen2.5-coder GGUF)
2. Start **v3 orchestrator** on `:8001`
3. Run **self-heal**: learn → discover(desktop/clean) → assemble → promote (dry) → cycle
4. Run **3 deepen loops** (each pass deeper)
5. Print health / capabilities / recovery

### Options

```powershell
# More deepen loops + actually apply promote queue (careful)
powershell -ExecutionPolicy Bypass -File C:\realai\scripts\run_local_selfheal.ps1 -DeepenLoops 5 -ApplyPromote

# Full discover (longest)
powershell -ExecutionPolicy Bypass -File C:\realai\scripts\run_local_selfheal.ps1 -DiscoverMode all -DeepenLoops 3

# Focus realai-clean + historical
powershell -ExecutionPolicy Bypass -File C:\realai\scripts\run_local_selfheal.ps1 -DiscoverMode clean

# Stack only
powershell -ExecutionPolicy Bypass -File C:\realai\scripts\run_local_selfheal.ps1 -SkipHeal -SkipDeepen

# Heal only (stack already up)
powershell -ExecutionPolicy Bypass -File C:\realai\scripts\run_local_selfheal.ps1 -SkipStart
```

---

## Manual step-by-step

### A) Environment (once per shell)

```powershell
cd C:\realai
$env:REALAI_SELF_IMPROVE="true"
$env:REALAI_VULKAN_BASE="http://127.0.0.1:8080"
$env:REALAI_API_BASE="http://127.0.0.1:8001"
$env:REALAI_DEFAULT_MODEL="realai-default-coder"
$env:REALAI_BACKEND_MODEL="qwen2.5-coder-7b-instruct-q5_k_m.gguf"
$env:PYTHONPATH="C:\realai"
```

### B) Start inference (Vulkan)

```powershell
# If not already running:
C:\llama-vulkan\llama-server.exe `
  -m C:\realai\models\qwen2.5-coder-7b-instruct-q5_k_m.gguf `
  --host 0.0.0.0 --port 8080 -c 8192 -ngl 99 --jinja
```

Or:

```powershell
powershell -File C:\realai\scripts\start_v3_stack.ps1
```

### C) Start orchestrator

```powershell
cd C:\realai
python -m realai.v3_orchestrator --host 127.0.0.1 --port 8001
```

### D) Self-heal via API (stack must be up)

```powershell
# Status
curl http://127.0.0.1:8001/v1/self-heal/status
curl http://127.0.0.1:8001/v1/self-heal/abilities

# Learn keywords
curl -X POST http://127.0.0.1:8001/v1/self-heal/learn-keywords -H "Content-Type: application/json" -d "{}"

# Discover gold (Desktop + realai-clean + more)
curl -X POST http://127.0.0.1:8001/v1/self-heal/discover -H "Content-Type: application/json" -d "{\"mode\":\"desktop\"}"
# or clean-focused:
curl -X POST http://127.0.0.1:8001/v1/self-heal/discover -H "Content-Type: application/json" -d "{\"mode\":\"clean\"}"
# or everything (long):
curl -X POST http://127.0.0.1:8001/v1/self-heal/discover -H "Content-Type: application/json" -d "{\"mode\":\"all\"}"

# Assemble promote queue from scan_results
curl -X POST http://127.0.0.1:8001/v1/self-heal/assemble -H "Content-Type: application/json" -d "{}"

# Promote dry-run
curl -X POST http://127.0.0.1:8001/v1/self-heal/promote -H "Content-Type: application/json" -d "{\"apply\":false}"

# Promote APPLY (writes files — only when queue looks good)
curl -X POST http://127.0.0.1:8001/v1/self-heal/promote -H "Content-Type: application/json" -d "{\"apply\":true}"

# Full dry cycle
curl -X POST http://127.0.0.1:8001/v1/self-heal/cycle -H "Content-Type: application/json" -d "{\"apply\":false}"
```

### E) Deepen loops (deeper each run)

```powershell
# Once
curl -X POST http://127.0.0.1:8001/v1/deepen -H "Content-Type: application/json" -d "{\"assemble\":true,\"hive\":true,\"cycle\":true}"

# Or CLI (3 times):
cd C:\realai
python -m realai.deepen_cycle --cycle
python -m realai.deepen_cycle --cycle
python -m realai.deepen_cycle --cycle
```

### F) CLI self-heal (no HTTP)

```powershell
cd C:\realai
$env:REALAI_SELF_IMPROVE="true"

python -c "from realai.self_heal import run_learn_keywords; print(run_learn_keywords().get('ok'))"
python -c "from realai.self_heal import run_discover; print(run_discover('desktop').get('ok'))"
python -c "from realai.self_heal import run_assemble; print(run_assemble().get('ok'))"
python -c "from realai.self_heal import run_promote; print(run_promote(apply=False).get('ok'))"
python -c "from realai.self_heal import run_full_cycle; print(run_full_cycle(apply_promote=False).keys())"

# Desktop / clean scanners directly:
python scanners\scan_desktop_missing_gold.py
python scanners\assemble_gold_index.py
python scanners\promote_gold.py
# apply:
python scanners\promote_gold.py --apply
```

---

## Verify chat works

```powershell
curl http://127.0.0.1:8001/health
curl http://127.0.0.1:8001/v1/models
curl -X POST http://127.0.0.1:8001/v1/chat/completions `
  -H "Content-Type: application/json" `
  -d "{\"model\":\"realai-default-coder\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply: RealAI online\"}],\"max_tokens\":32}"

curl -X POST http://127.0.0.1:8001/v1/embeddings `
  -H "Content-Type: application/json" `
  -d "{\"input\":\"hello\",\"model\":\"realai-embeddings\"}"
```

---

## What to read after a run

| File | Meaning |
|------|---------|
| `scan_results\deepen_last.md` | Latest deepen pass |
| `scan_results\self_heal_last_cycle.md` | Last heal cycle |
| `scan_results\desktop_missing_gold_map.md` | Desktop + realai-clean gold |
| `scan_results\promote_queue.json` | What promote will do |
| `scan_results\ability_catalog.json` | Ability coverage |
| `logs\vulkan.err.log` | Inference log |
| `logs\v3-orchestrator.err.log` | Orchestrator log |

---

## Discover modes cheat-sheet

| mode | What it does |
|------|----------------|
| `desktop` | OneDrive Desktop + Documents + Downloads + **realai-clean** + more |
| `clean` | same scanner (includes realai-clean, historical, GitHub) |
| `local` | desktop + broader keyword scan |
| `operational` | dds3 operational + archive triage |
| `abilities` | ability inventory + keyword learn |
| `deep` | deep gold map |
| `all` | everything (longest) |
| `learn` | keywords/catalog only (fast) |
