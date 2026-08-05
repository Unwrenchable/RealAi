# Deep Discovery Report — Models, Ports, Gold Map

**Date:** 2026-07-13

## 1. Why chat/UI “worked once then never”

### Port split (smoking gun)

| Source | Value | Effect |
|--------|-------|--------|
| `.env` **before fix** | `PORT=8082`, `REALAI_API_BASE=http://127.0.0.1:8082` | Clients/UI aim at **8082** |
| `realai.toml` | `port = 8000` | Config says **8000** |
| Boot gate server | `python -m realai.api_server --port 8000` | Process on **8000** only |
| Port 8082 | **Nothing listening** | UI hits dead endpoint |

This matches “v2 took over v3 / ran once or twice never again”: one process on 8000, tooling still pointed at **8082** (or leftover server later died). Not necessarily evil malware — **misaligned ports**.

**Fixed now:** `.env` → `PORT=8000` and `REALAI_API_BASE=http://127.0.0.1:8000`  
Backup: `.env.pre_port_fix.bak`

### Leftover servers (live check)

| Port | Process | Notes |
|------|---------|-------|
| 8000 | `python -m realai.api_server` | Current healthy boot server |
| 8082 | empty | Old client target — dead |
| 3000 / 5173 / 11434 | empty | No competing frontends/ollama |

Only one RealAI API process was found.

---

## 2. Deep model inventory — intentional stubs, not full weights

**Output:** `scan_results/deep_model_inventory.json`

| Metric | Count |
|--------|------:|
| GGUF files found (noise pruned, archive/OG/backups included) | **40** |
| GGUF ≥ 50 MB (usable LLM weights) | **0** |
| GGUF < 50 MB (stubs) | **40** (~1.5–1.8 MB each) |
| `.safetensors` | **0** |
| Large `.bin` weights | **0** |
| Model-ish configs | **115** |

Stub GGUFs are **valid GGUF headers** (`GGUF` magic, architecture=`llama`) but **no tensor payload** — placeholders so paths/registry resolve without shipping multi‑GB files (or downloads never finished).

**Conclusion:** Models were effectively **left out** (or only stubbed). You cannot get real local chat until:

1. Download real GGUF (hundreds of MB–GB), or  
2. Use cloud API key + `X-Provider`, or  
3. Point at an external Ollama/vLLM that has weights

`realai.toml` wants `default_chat_model = "llama-local"` and `default_embedding_model = "realai-embed"` — registry names exist; **weights do not**.

---

## 3. Deep gold map (what cavity scripts were trying to do)

**Scanner:** `scanners/dds3_deep_gold_map.py`  
**Outputs:**  
- `scan_results/dds3_deep_gold_map.json`  
- `scan_results/dds3_deep_gold_map_summary.json`

### Design (your requirements)

| Include | Skip |
|---------|------|
| `.md` `.txt` `.py` `.ts` `.js` configs | `node_modules`, `venv`, `site-packages` |
| Nested `archive/`, `realai_og_mess/`, `.backup/` any level | `.next`, `dist`, phase4 previews |
| Capability keyword groups (models, agents, memory…) | Multi‑MB junk, lockfiles, `repo_tree*.txt` |

**Runtime:** ~27s · **4359 files scanned** · **4337 with gold hits**

### Gold density by group

| Group | Hits |
|-------|-----:|
| models_inference | 5452 |
| server_api_ui | 3775 |
| agents_orchestrate | 2834 |
| tools_mcp_plugins | 2821 |
| missing_broken (todo/stub/placeholder) | 2601 |
| web3_solana | 1615 |
| v2_v3_migration | 1273 |
| memory_rag | 931 |
| self_improve_training | 905 |
| world_npc_game | 698 |

### Gold by era (why nested matters)

| Era | Files with gold |
|-----|----------------:|
| backup | 1661 |
| og_mess | 1569 |
| clean | 526 |
| archive | 330 |
| other | 158 |

Most keyword gold still lives in **backups + OG mess** — operational DDS-3 alone cannot see the full map; deep gold mode is the right layer for that without re-running multi‑GB cavity dumps.

### Top keywords (signal)

`embedding`, `llama`, `plugin`, `web3`, `orchestrat`, `stub`, `placeholder`, `chat/completions`, `gguf`, `streaming`, `openai-compatible`, `training`, `api_server`, …

High **stub/placeholder/missing** counts align with boot: API surface is real; inference is not.

---

## 4. How the puzzle layers fit now

```
Operational DDS-3     → missing modules + archive triage (boot path)
Deep model inventory  → prove weights exist or not (they don't)
Deep gold map         → md/txt + nested OG/archive capability map
.env port fix         → stop UI shooting 8082 while server is 8000
Boot gate             → server healthy on 8000
```

**Do not re-run** multi‑GB `realai_alt_cavity_manifest` crawls. Deep gold + model inventory replace that need with scoped, readable outputs.

---

## 5. Next actions (recommended order)

1. **Use UI against 8000** — open http://127.0.0.1:8000/ (server already up)  
2. **Get real weights or cloud key** — stubs will never chat for real  
3. **Optional:** wire `llama-local` registry to a real GGUF path once downloaded  
4. **Optional:** re-run deep gold after more recovery to track only_outside_clean shrinkage  

### Commands

```powershell
# deep gold (md/txt + nested, noise skipped)
python scanners/dds3_deep_gold_map.py

# model weight hunt
python -c "..."  # or open scan_results/deep_model_inventory.json

# server
python -m realai.api_server --host 127.0.0.1 --port 8000
```
