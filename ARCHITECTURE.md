# RealAI architecture — one product, one tree

**Branch authority:** `live/realai-clean-20260911` is the product.
This file is the layout contract. Older docs (`docs/architecture.md`, `docs/structure.md`, root `AGENTS.md`) describe earlier eras. When they disagree, this file wins.

v1, v2, and v3 are **layers of one intelligence**, not sibling repos and not version folders. Code from every era that is still useful lives *inside* the live package under a stable name.

---

## Runtime (what actually runs)

```
Operator / VS Code / browser
        |
        v
  Hive gateway  :8001     python -m realai.v3_orchestrator
        |                   shim → realai.orchestration.v3_orchestrator  (gold)
        +-- tools / abilities / multi-agent
        +-- plugins (RackUp coach, ratings, SOTD, training hooks)
        +-- organs hive
        +-- self_heal / self_builder / closed_loop
        v
  Vulkan llama-server :8080     local GGUF (not in git)
```

Cloud twin: `python -m realai.api_server` (OpenAI-compatible, Render).

---

## Target tree (professional monorepo)

Edit **product-root** copies. The Python package is `realai/`.

```
RealAI-clean/                      # REALAI_HOME — product home
│
├─ README.md                      # what it is + how to run
├─ ARCHITECTURE.md                # this file
├─ ABILITIES.md                   # operator surface
├─ ANY_REPO.md                    # foreign-workspace mode
├─ realai.toml / models.yaml / providers.yaml
│
├─ realai/                        # THE Python package (import realai)
│   ├─ orchestration/              # gold hive (v3 + inherited v1/v2 orchestrators)
│   ├─ core/                       # engine, memory, self_builder, safety
│   ├─ server/                     # OpenAI-compatible HTTP
│   ├─ cli/                        # `realai` / craft / stack
│   ├─ plugins/                    # plugin authority (rackup_coach, training, …)
│   ├─ agents/                     # roster + runtimes Hive loads
│   ├─ voice/                      # ASR / TTS / Voice Lab
│   ├─ training/                   # LoRA / pipeline hooks
│   ├─ tools.py + tools/           # TOOL_REGISTRY
│   ├─ ability_catalog.py          # honesty map
│   └─ agent_tools_gold/           # sandboxed executor gold
│
├─ abilities/                     # ability handlers (product-root)
├─ agents/                        # agent manifests (product-root)
├─ modules/organs/                # synthetic organs hive
├─ modules/orchestrators/         # worker entry (`realai-worker`)
│
├─ apps/
│   ├─ vscode/                    # RealAI Console extension
│   ├─ frontend/                  # parked Next shell (prefer root frontend/)
│   └─ api/                       # ASGI helpers if needed
├─ frontend/                      # Next.js UI (Vercel)
├─ packages/
│   ├─ design-system/
│   ├─ sdk-py/
│   └─ sdk-ts/
│
├─ scanners/                      # promote / DDS / gold tools (not runtime)
├─ scripts/                       # bats + operators
├─ tests/
├─ docs/                          # human docs (this contract lives at root too)
├─ _quarantine/                   # pointer only — archive on D:\
└─ recovered/ / imports/          # archaeology; never imported by runtime
```

Weights stay **outside git**: `C:\llama-vulkan\models`, `C:\models`, `D:\models`.

---

## Lineage → live module (do not recreate version folders)

| Era | What it contributed | Lives in live as |
|-----|---------------------|------------------|
| **v1** | Local provider, API shapes, frontend/vscode, adapters, first orchestrator | `realai/server`, `realai/core`, `apps/vscode`, `frontend/`, `packages/` |
| **v2** | Agent-tools, plugins, self-heal / self-improve, training, desktop UI kit, organs | `realai/plugins`, `realai/agent_tools_gold`, `realai/self_heal.py`, `realai/core/self_*`, `modules/organs`, `packages/design-system` |
| **v3** | Hive gateway, runtime bridge, multi-agent, ability catalog, Craft/console | `realai/orchestration/v3_*`, `realai/ability_catalog.py`, `realai/cli` |

Import names stay stable:

```python
import realai.v3_orchestrator          # shim → orchestration gold
import realai.v3_runtime_bridge        # shim → orchestration gold
import realai.self_builder             # shim → core gold
import realai.plugins                  # plugin authority
```

There is no `v1/` or `v2/` directory on purpose.

---

## Authority (where to edit)

| Concern | Edit here | Do not edit |
|---------|-----------|-------------|
| Hive HTTP / tools / multi-agent | `realai/orchestration/v3_orchestrator.py` | root `v3_orchestrator.py` shims |
| Runtime bridge | `realai/orchestration/v3_runtime_bridge.py` | dest-empty shims |
| Plugins | `realai/plugins/` | root `plugins/` (compat shim) |
| Abilities | product-root `abilities/` | `realai/plugins/abilities` parked phase 3 (Hive loads `rackup_coach`, not that tree) |
| Organs | `modules/organs/` | copies under `realai/modules/organs` |
| Self-build / closed loop | `realai/core/` | 200-byte package-root shims |
| UI tokens | `packages/design-system/` | ad-hoc CSS at repo root |
| Recovery snapshots | stay on `recovery/*` branches | never merge onto live |

---

## What makes live look unprofessional today

Keep the gold. Park the rest.

1. **Root junk drawer** — `layout.tsx`, `globals.css`, `Hey — I'm here..txt`, twenty `start_*.bat`, `world_model.json` at root.
2. **Nested dumps inside the package** — `realai/realai`, `realai/realai_repo`, `realai/grok_export_realai`, `realai/deep_nests`, `realai/plugins/plugins`.
3. **Twin trees** — product-root `agents/` vs `realai/agents/`; root `plugins/` vs `realai/plugins/`.
4. **Wrong front door** — root `AGENTS.md` is a Grok App Builder sandbox contract, not RealAI.
5. **Stale version label** — `pyproject.toml` still says `version = "2.0.0"` while the product is the v3 hive.
6. **Conflicting architecture docs** — May 2026 JS-engine blueprint vs current Python hive.

Physical moves happen in `docs/REORG_PHASES.md`. Do not mega-merge `main` or `recovery/*`.

---

## How future work is added

1. New runtime code goes in `realai/<pillar>/` (orchestration, core, plugins, voice, training).
2. New operator-facing ability goes in `abilities/<name>.py` **and** a row in `realai/ability_catalog.py`.
3. New plugin is a package under `realai/plugins/<name>/` with a manifest.
4. New UI goes in `frontend/` or `apps/vscode/`, tokens from `packages/design-system`.
5. Archaeology / recovered files land in `_quarantine` or stay on a `recovery/*` branch until `scanners/promote_gold.py` beats live gold on size + symbols.
6. Never add `v4/` as a parallel tree. v4 is more modules in the same package.
