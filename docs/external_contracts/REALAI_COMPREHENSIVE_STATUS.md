# RealAI — Comprehensive Status Rundown

**Document date:** 2026-08-05  
**Workspace:** `C:\realai`  
**Living branch:** `unification/ultimate-all`  
**HEAD (pushed):** `04c43acb` — *feat(rackup-coach): full RackUp Pyramid rules + ability fusion*  
**Remote:** `origin` → `https://github.com/Unwrenchable/RealAi.git`  
**Tracking:** `unification/ultimate-all` is **up to date** with `origin/unification/ultimate-all`

---

## 1. What RealAI is (locked stance)

RealAI is a **full local-first OpenAI-compatible provider**, not a thin wrapper or router around external models.

| Layer | Role |
|-------|------|
| Runtime | Agent runtime, hierarchical pipelines, tools |
| Inference | Local backends (llama.cpp / stubs / local-first routing) |
| Models | realai-* family registry, embeddings hooks |
| Memory | SQLite + long-term engine + aura / episodic / semantic concepts |
| Agents | Planner / critic / executor / synthesizer + hierarchical / RISE / supervisor |
| Organs hive | 44 synthetic organs + plugin organs (45 total registered) |
| Plugins | Living plugins (e.g. `rackup-coach`) |
| API | OpenAI-style `/v1/*` + RealAI extensions (organs, hive, rackup) |
| External APIs | Optional adapters only (Grok, OpenAI, etc.) |

---

## 2. Where unification stands (high level)

| Phase | Status | Notes |
|-------|--------|--------|
| Phase 0–4 analysis / DDS scanners | **Done earlier** | Multi-era super-repo scanned; DDS-3 was the long path mapper |
| Source-only recovery pushes | **Largely done** | Large multi-GB artifacts moved to giant hold, not deleted |
| `unification/ultimate-all` created from `realai` | **Done** | Living integration branch |
| Batch 1 snapshots → `recovered/` | **Done** | Desktop + nested + RealAIProject + real-fin |
| Batch 2 snapshots → `recovered/` | **Done** | 22 recovery/local tips (unique-modules, agents-skills, etc.) |
| Batch 3 snapshots → `recovered/` | **Done** | 23 more (clean-base, plugin-boards, recycle-py, desktop-*, etc.) |
| Living promotions (training/memory/agents/orch) | **Done** | Core + modules packs |
| 44 synthetic organs hive | **Done** | Callable via `hive_status` / `call_organ` |
| Deep organ request-path fusion | **Done** | Chat, orchestrate, API organs routes |
| Unique-code sweep | **Done** | Report in repo `docs/unification/SWEEP_REPORT.md` |
| **rackup-coach** living plugin | **Done** | v1.1.0 with full Pyramid rules |
| Recycle-bin / nested-repo gold exhaust | **Partial** | Snapshots + promotions done; forensic dirs still untracked |
| ability_catalog → TOOL_REGISTRY auto-load | **Not done** | File living; not auto-merged |
| Every organ hard-wired into every API route | **Partial** | Chat/orchestrate/self-improve/organs/* yes; embeddings/audio softer |
| Linear merge of 60 histories | **Out of scope** | Snapshots under `recovered/` instead |

**Bottom line:** The **living unified system exists and is pushed**. Unique development is largely **archived under `recovered/` (~55 tips)** and **selectively promoted**. RackUp coaching is a first-class plugin with locked Pyramid rules. Remaining work is **deeper wiring, forensic cleanup, and product polish** — not “starting unification.”

---

## 3. Git timeline (recent living commits)

| SHA | Summary |
|-----|---------|
| `04c43acb` | RackUp Pyramid full rules + ability fusion |
| `8d3227e3` | Living `rackup-coach` plugin + `organ.rackup-coach` |
| `b4e91a37` | Final unique-code sweep + organ request-path fusion |
| `e097a129` | Batch 3 recovery/local tip snapshots |
| `11eb754e` | 44 synthetic organs hive |
| `7d003b4e` | Batch 2 + promote training/memory/agents/orchestration |
| `6871a473` | Batch 1 recovered snapshots + registry/adapters scaffold |
| `11f25c80` | Base `realai` scaffolding (branch point) |

---

## 4. Living tree architecture

```
C:\realai\
  realai/                 # Package: API, runtime, memory, tools, identity, world_model, ...
  core/                   # Living core: agents, memory, training, orchestration, inference, tools, voice, web3
  modules/
    organs/               # 44 synthetic organs + hive + request_path fusion
    self_improvement/     # closed_loop, self_builder, SI agents
    agents_advanced/      # code_engineer, overmind
    agents_skills/        # promoted agents pack
    desktop_unique/       # lambda + local CLI
    training/datasets/    # finetune jsonl assets
    orchestrators/        # orchestrator variants
  plugins/
    rackup_coach/         # import package (id: rackup-coach)
    rackup-coach/         # manifest + README (plugin id path)
  adapters/               # discovery: training, memory, agents, organs, self_improvement, rackup_coach
  registry/modules.yaml   # module registry
  recovered/<slug>/       # ~55 branch tip snapshots (never delete)
  docs/unification/       # BRANCH_MAP, SWEEP_REPORT, PROVIDER_STATUS, GOLD_DEEP_SCAN, batch results
```

### Giant hold (not in git; not deleted)

`C:\realai_giant_hold\` — multi-GB archives, gguf/node_modules/venv extractions moved out for push safety.

### Still untracked local forensic (not on GitHub)

| Path | Notes |
|------|--------|
| `recovered/from_recycle_bin/` | Large forensic extract; unique gold mostly also in batch snapshots |
| `realai_og_mess/` | OG nest |
| `_hold_untracked_*` | Local hold |

---

## 5. Organs hive status

| Metric | Value |
|--------|--------|
| Base synthetic organs | **44** (complete) |
| Total registered now | **45** (+ `organ.rackup-coach`) |
| Categories | cognitive 8, nervous 3, dream 4, body 7, metabolic 4, evolution 4, memory 8, meta 7 |

**API surfaces:**

- `GET /v1/organs`, `/v1/organs/status`, `/v1/hive`
- `POST /v1/organs/invoke`, `/v1/organs/pipeline`
- Chat path: organ enrichment on `/v1/chat/completions` (disable via `organs:false` or `X-RealAI-Organs: 0`)
- Orchestrate: organs pre-pass on `/v1/agents/orchestrate`
- `POST /v1/self-improve/cycle`

**Python:**

```python
from modules.organs import hive_status, call_organ
hive_status()  # organ_count >= 44
call_organ("organ.hippocampus", goal="...")
call_organ("organ.rackup-coach", goal="pyramid shot of the day", payload={...})
```

**Honest gaps:** not every `/v1/*` route runs organs (embeddings/audio lighter); guardian is advisory not hard sandbox; dream organs not scheduled.

---

## 6. rackup-coach plugin (product surface)

| | |
|--|--|
| Plugin id | `rackup-coach` |
| Package | `plugins.rackup_coach` |
| Version | **1.1.0** |
| Organ | `organ.rackup-coach` |
| HTTP | `POST /v1/plugins/rackup-coach`, `POST /v1/rackup/coach` |

### Abilities

| Ability | Purpose |
|---------|---------|
| `coach` / `pyramid` | Rating- and Pyramid-aware coaching, practice plans, mental, pre-match |
| `shot_of_the_day` | Practical daily shot (incl. Pyramid variants) |
| `moderation` | Toxicity, harassment, money drama, sandbagging |
| `video_analysis` | Host checklist/notes → structured feedback + drills |
| `matchmaking` | Candidate ranking; Pyramid table/skill + rating weights |
| `rating_intel` | Trajectory + Pyramid skill weights |
| `tournament` | Event prep |
| `hall_context` | Hall/session + table size → rack |
| `pyramid_rules` | Full locked matrix + race context |

### RackUp Pyramid (locked rules — implemented)

| Skill | 7 ft (10-ball) | 9 ft (15-ball) | Call shot | Rating weight |
|-------|----------------|----------------|-----------|---------------|
| Beginner | 25 | 40 | No | 0.7× |
| Intermediate | 35 | 55 | No | 0.85× |
| Advanced | 45 | 71 | Optional | 1.0× |
| Pro | 50 | 71 | Yes | 1.15× |

- Classical scoring: ball number = points; **1-ball = 11**
- Designated cue ball only; first to target wins
- Classical mindset coached on American tables

```python
from plugins.rackup_coach import invoke
invoke({
  "ability": "shot_of_the_day",
  "player": {
    "player_id": "p1", "discipline": "pyramid",
    "table_size": "7ft", "skill_level": "intermediate", "rating": 620,
    "weaknesses": ["pattern_play"],
  },
  "payload": {"game": "pyramid"},
})
```

Full call signatures: `plugins/rackup_coach/examples/call_signatures.md`

---

## 7. Recovery / snapshot inventory

- **~55** tip folders under `recovered/<slug>/` (batch 1 + 2 + 3)
- Includes: nested-realai, desktop-*, primary-clean, unique-modules, agents-skills, plugin-boards, recycle-py-unique, clean-base, RealAi-unified, from-wsl, grok-*, users-tsmit-*, etc.
- **Principle:** never delete recovered snapshots; promote copies into living tree

Repo docs:

- `docs/unification/BRANCH_MAP.md`
- `docs/unification/batch1_import_results.json`
- `docs/unification/batch2_import_results.json`
- `docs/unification/batch3_import_results.json`

---

## 8. Promoted living modules (selected)

| Destination | Source class |
|-------------|--------------|
| `core/training/*` | DirectML/Qwen trainers, finetune, training_pipeline |
| `core/memory/*` | base + long_term_engine + bridge |
| `core/agents/*` | hierarchical, rise, supervisor, self_heal, agent_runtime |
| `core/orchestration/*` | v3 + gold pipeline |
| `realai/ability_catalog.py` | 33k ability catalog |
| `realai/agent_protocol.py`, `aura_memory.py` | protocol + aura |
| `modules/self_improvement/*` | closed_loop, self_builder, SI agents |
| `modules/agents_advanced/*` | code_engineer, overmind |
| `modules/desktop_unique/*` | lambda + local_model_cli |
| `plugins/rackup_coach/*` | full coach + Pyramid |

Reports: `docs/unification/SWEEP_REPORT.md`, `PROMOTE_PASS.md`, `GOLD_DEEP_SCAN.md`

---

## 9. Completeness scorecard

| Area | Completeness | Comment |
|------|--------------|---------|
| Unification branch exists & pushed | **100%** | `ultimate-all` |
| Snapshot archive of major branches | **~90%** | 55 tips; a few local-only multi-GB may remain |
| Living core packages | **85%** | Strong; some deps soft-fail |
| Organs (44 base) | **100% present** | Deeper path fusion ~70% |
| Registry / adapters | **80%** | Entries exist; not all auto-loaded at runtime |
| rackup-coach + Pyramid | **95%** | Rules locked; host integration pending on RackUp app |
| Unique gold promotion | **75%** | Best of each promoted; forks left as snapshots |
| Forensic recycle exhaust | **40%** | Untracked; scan says mostly dupes |
| Production hardening / tests | **40%** | Smoke tests ad hoc; CI not fully proven here |
| Docs for operators | **70%** | unification docs + this rundown |

**Overall unification maturity: ~80% toward “one living system with zero unique code lost.”**  
Remaining 20% is wiring polish, forensic optional, app integration, and tests — not missing the whole product.

---

## 10. What is *not* done / risks

1. **`ability_catalog` not auto-wired into `TOOL_REGISTRY`**
2. **Guardian organ does not hard-block tools** (advisory)
3. **Embeddings/audio routes** lighter organ fusion
4. **Untracked forensic trees** still only on disk
5. **Promoted modules may need optional pip packages** at import time
6. **Repo size heavy** from large recovered snapshots (including some vendor binaries in recycle-py)
7. **a13f9c-class multi-GB local branches** — source-only push only if still needed
8. **RackUp app (NestJS/DB)** is out of band — coach is pure AI provider capability

---

## 11. Recommended next steps (ordered)

1. Wire `realai.ability_catalog` into tools registry load path  
2. Integration tests: organs API + rackup-coach Pyramid matrix (all 8 skill×table)  
3. Optional: selective promote from `from_recycle_bin/hive_priority_uniques` after manual diff  
4. RackUp host: call `POST /v1/plugins/rackup-coach` with player + pyramid fields  
5. Soften repo weight later (document-only LFS policy; keep snapshots)  
6. Continue deeper recycle/nested scan only for **basename-unique** modules not already living  

---

## 12. Quick commands

```powershell
cd C:\realai
git checkout unification/ultimate-all
git pull origin unification/ultimate-all

# Organs
$env:PYTHONPATH = "C:\realai"
python -c "from modules.organs import hive_status; print(hive_status()['organ_count'])"

# RackUp Pyramid
python -c "from plugins.rackup_coach import invoke; print(invoke({'ability':'pyramid_rules','player':{'player_id':'x','table_size':'7ft','skill_level':'pro','discipline':'pyramid'}})['result']['config'])"
```

---

## 13. Related documents (in-repo)

| File | Purpose |
|------|---------|
| `docs/unification/README.md` | Unification layout |
| `docs/unification/PROVIDER_STATUS.md` | Provider-level status |
| `docs/unification/SWEEP_REPORT.md` | Missed-items / unique-code sweep |
| `docs/unification/GOLD_DEEP_SCAN.md` | Post-Pyramid gold scan |
| `docs/unification/BRANCH_MAP.md` | Snapshot map |
| `plugins/rackup_coach/README.md` | Plugin overview |
| `plugins/rackup_coach/examples/call_signatures.md` | Host call API |
| `plugins/rackup_coach/pyramid.py` | Locked Pyramid rules |

---

## 14. One-sentence summary

**RealAI’s living branch `unification/ultimate-all` (@ `04c43acb`) is a pushed, provider-level system with ~55 recovered branch snapshots, promoted core/modules, a complete 44-organ hive (+ RackUp organ), deep organ fusion on key API paths, and a full `rackup-coach` plugin including locked Pyramid rules for all skill levels on 7ft and 9ft tables — remaining work is wiring polish, optional forensic gold, and host/app integration, not rebuilding the core.**

---

*Saved to: `C:\Users\tsmit\realai_documents\REALAI_COMPREHENSIVE_STATUS.md`*
