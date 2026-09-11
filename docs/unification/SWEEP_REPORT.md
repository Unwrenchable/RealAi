# Final Missed-Items + Unique-Code Sweep Report

**Branch:** `unification/ultimate-all`  
**Base HEAD before pass:** `e097a129`  
**Provider stance:** Full local-first OpenAI-compatible provider (not a wrapper).

## 1. Newly discovered unique code

| Path | Description | Recommendation |
|------|-------------|----------------|
| `recovered/.../ability_catalog.py` (33k) | Full ability/tool catalog | **Promoted** → `realai/ability_catalog.py` |
| `recovered/.../hierarchical_agent.py` | Desktop hierarchical agent | **Promoted** → `core/agents/` + `realai/` |
| `recovered/.../rise_system.py` | RISE agent system | **Promoted** → `core/agents/` |
| `recovered/.../supervisor.py` | Multi-agent supervisor | **Promoted** → `core/agents/` |
| `recovered/.../training_pipeline.py` | Agent training pipeline | **Promoted** → `core/training/` |
| `recovered/.../closed_loop.py` | Self-improvement closed loop | **Promoted** → `modules/self_improvement/` |
| `recovered/.../self_builder.py` | Self-builder (13k) | **Promoted** → `modules/self_improvement/` |
| `recovered/.../self_improving_agent.py` | SI agent variants | **Promoted** → `modules/self_improvement/` |
| `recovered/.../agent_protocol.py` | Agent protocol types | **Promoted** → `realai/agent_protocol.py` |
| `recovered/.../aura_memory.py` | Aura memory bridge | **Promoted** → `realai/aura_memory.py` |
| `recovered/.../code_engineer_agent.py` | Code engineer agent | **Promoted** → `modules/agents_advanced/` |
| `recovered/.../overmind_runner.py` | Overmind runner | **Promoted** → `modules/agents_advanced/` |
| `recovered/desktop-unique-py-*/` (11 modules) | Lambda + local CLI + examples | **Promoted** → `modules/desktop_unique/` |
| `plugin-boards` / `recycle-py-unique` (300+ basename-only py) | Many api_server_* forks, scanners, vendor binaries | **Leave as snapshot** — duplicates/junk; gold pieces promoted above |
| `recovered/from_recycle_bin/` (untracked, 13k+ py) | Forensic extract + hive_priority_uniques | **Leave untracked**; unique gold largely already in batch2/3 snapshots |
| `_hold_untracked_*` (7 py) | Local hold | **Leave outside git** |
| `realai_og_mess` (345 py) | OG mess nest | **Leave untracked**; og-mess-clean snapshot already in recovered/ |
| `C:\realai_giant_hold\` | Multi-GB archives | **Hold only** — not deleted |

## 2. Modules still missing / incomplete

| Item | Status |
|------|--------|
| Full fusion of every organ into every API route | Partial — chat, orchestrate, self-improve, organs/* done |
| ability_catalog wired into TOOL_REGISTRY auto-load | Incomplete — file living, not yet auto-merged into tools |
| closed_loop class API may not match import assumptions | Soft-fail in `/v1/self-improve/cycle` |
| Vendor llama.exe under recycle-py snapshot | Present in snapshot only; not promoted to living |
| Extra organs beyond 44 | None found as distinct first-class designs |

## 3. Organs deeper wiring (gaps closed this pass)

| Gap | Fix |
|-----|-----|
| Soft-link only | `modules/organs/request_path.py` real pipeline |
| No API surface | `GET /v1/organs`, `/v1/organs/status`, `/v1/hive`; `POST /v1/organs/invoke`, `/v1/organs/pipeline` |
| Chat path | `enrich_chat_messages()` in `/v1/chat/completions` (disable via `organs:false` or `X-RealAI-Organs: 0`) |
| Orchestration path | `orchestrate_with_organs()` in `/v1/agents/orchestrate` |
| Agent runtime | Organs run before `MultiAgentPipeline` stages; `run_with_organs()` helper |
| Self-improvement | `POST /v1/self-improve/cycle` + evolution organs |

### Remaining organ gaps
- Embeddings/audio routes do not yet call sensory/respiratory organs
- Dream organs not on a nightly scheduler (API-trigger only)
- Guardian organ not yet hard-enforcing tool sandbox (advisory notes only)

## 4. Promotions (source → destination)

See section 1. All highest-priority unique pieces from desktop-unique-py, unique-plugins, agents-skills gold, unique-modules ability_catalog.

## 5. Registry entries added

- `realai-ability-catalog`, `realai-agent-protocol`, `realai-aura-memory`
- `core-agents-hierarchical`, `core-agents-rise`, `core-agents-supervisor`
- `core-training-pipeline`
- `modules-self-improvement`, `modules-agents-advanced`, `modules-desktop-unique`
- `organs-request-path` (+ prior `modules-organs-hive`)

## 6. New organs beyond 44?

**None required.** No recovered design documents define a 45th distinct organ. Meta-layers (intuition/inspiration/creativity/paradox/consciousness/soul) already cover chat-only “extra” concepts.

## 7. Conflicts / duplicates

| Cluster | Resolution |
|---------|------------|
| plugin-boards ≈ from-accident ≈ recycle-py basename sets | Keep snapshots; promote single strongest copy each |
| hierarchical_agent / rise / supervisor repeated 10+ times | One living copy under `core/agents/` |
| identity/critique/world_model already living (equal size) | No overwrite |
| Multiple api_server_* fork names | Snapshot only |

## 8. Concrete next steps (ordered)

1. Wire `ability_catalog` into `realai.tools.TOOL_REGISTRY` load path.
2. Add organ hooks to embeddings + tool validate (sensory/guardian).
3. Optional: promote selected `from_recycle_bin/hive_priority_uniques` files after manual diff.
4. Source-only orphan push for any remaining multi-GB a13f9c locals if still needed.
5. Integration tests for `/v1/organs/*` and organ-enriched chat.

## 9. Honest remaining risks

- **Import-time fragility:** promoted modules may depend on packages not in requirements; imports are try/except where possible.
- **Large snapshots on branch:** recycle-py includes vendor binaries — repo size heavy but unique code preserved.
- **Forensic untracked:** `from_recycle_bin` still local-only by design (noise); re-scan if gold appears missing.
- **Closed-loop API shape unknown** until first real run of promoted closed_loop.py.
- **Organs do not replace models** — they annotate/route; inference still via RealAI backends.

## 10. Verification (this pass)

```
organs_enabled True
injected True results 5
hive organ_count 44
ability_catalog present
```
