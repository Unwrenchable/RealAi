# RealAI Consolidation Plan — "Unity Through Modularity"

## Context

The RealAI repo at `C:\Users\tsmit\realai` is a **single, multi-layered AI ecosystem** that has been built up over many versions (V0 megamodule → V1 llama.cpp sub-process → V2 cloud + Tkinter GUI → V3 modular server). All versions are legitimate layers of the same living system — none should be deleted. The current mess is that:

- The root mixes **canonical** code (V3 modular server), **legacy** code (V1/V2 entry points, V0 megamodule body), and **dead debris** (40 MB of `dir /S` snapshots, 642 MB PyInstaller exe, stray pip logs, IDE session transcript).
- **Three Python "core" roots** (`realai/`, `core/`, `realai-core/`) coexist, two HTTP servers (`realai/api_server.py` legacy BaseHTTPRequestHandler vs. `realai/server/app.py` canonical FastAPI), and two model-registry layouts (`models/models/registry.json.example` vs. `models.yaml`).
- The TypeScript side has a **monorepo** (`apps/`, `packages/`, `providers/`) plus an **orphan framework** (`core/index.ts`, `agents/devops_agent.ts`, `autopilot/`, `src/` duplicate Next page) kept alive only by the root `pnpm autopilot` script.
- **`solana-client/`** is a Jupiter-v1 swap executor sitting at the repo root — it's a sibling project, not RealAI.

**Outcome we want**: From `ls`, anyone can see what is canonical, what is legacy, and what is an external sibling. Old versions stay (lineage), each bucket exposes one API surface, cross-bucket imports are forbidden. The user explicitly asked for **integration over isolation** — old code is rehomed, not deleted.

**Hard constraints**:
- Phase 1 must be **zero behavior change**. Every test that passes today (31/36) passes after Phase 1.
- `realai:main` (the `pyproject.toml` console script) must keep working.
- `from realai import RealAI, RealAIClient, PROVIDER_CONFIGS, ModelCapability` (used by `realai/sdk/__init__.py`, `test_realai.py`) must keep working.
- Root `api_server.py` and `main.py` keep working as launchers.

---

## Final State (after Phase 1)

```
realai/                  canonical Python V3 package (realai/server, realai/training, realai/self_builder, realai/_v0_compat)
apps/  packages/  providers/   canonical TS monorepo
models/  checkpoints_lora/    model artifacts
realai.toml  models.yaml  providers.yaml  pyproject.toml  pnpm-workspace.yaml  package.json
api_server.py  main.py  start_realai.bat  start_self_build.bat   root shims/launchers
README.md  QUICKSTART_LOCAL.md  REALAI_3.0.md  docs/  tests/   canonical docs
.env  .env.example  .env.local
realai_local_server.py  test_local_server.py  test_realai.py   small kept-as-is
vendor/                 vendored C++ (llama.cpp)
solana-client/          EXTERNAL SANDBOX SIBLING (fenced, not RealAI)
legacy/
  v0-megamodule/        V0 seed (realai/__init__.py body) — importable for lineage
  v1-llama-cpp/         V1 BaseHTTPRequestHandler + local_models + TS devops framework
  v2-cloud-gui/         V2 Tkinter GUI + Vercel shim + build artifacts
```

`tree -L 1` (excluding `.git`, `node_modules`, `__pycache__`) makes the canonical surface obvious.

---

## Phase 1 — Re-home, zero behavior change

### 1A. Delete dead debris (zero behavior risk)

Delete these (they are checked-in artifacts, not lineage):

| File | Size | Reason |
|---|---|---|
| `repo_tree.txt` | 40 MB | `dir /S` snapshot |
| `repo_tree_clean.txt` | 37 MB | duplicate snapshot |
| `repo_tree_filtered.txt` | 14 MB | duplicate snapshot |
| `repo_tree_shallow.txt` | 20 B | broken 20-byte artifact |
| `6.0` | 9 KB | stray pip log with version-pin filename |
| `=10.4.0` | 9 KB | stray pip log with version-pin filename |
| `"from fastapi import APIRouter, Requ.txt"` | <1 KB | source fragment whose filename was the import line |
| `PAGES` | 3 B | trivial empty file |
| `copilot-session-39a9656a-48d7-4b7a-8ad4-aa82a2c153ee.txt` | 522 KB | IDE session transcript |
| `train_qwen_directml.py` | 2.7 KB | byte-identical duplicate of `train_directml.py` |
| `node_modules.disabled/` | many MB | pre-pnpm snapshot |
| `package-lock.json` | 15 KB | stale npm lockfile (pnpm-lock.yaml is canonical) |
| `Output/RealAI-Setup.exe` | 642 MB | PyInstaller artifact — KEEP, move to `legacy/v2-cloud-gui/Output/RealAI-Setup.exe` (unified packaged form of RealAI — see 1C under V2 bucket for README note). |
| `Output/img_*.png`, `Output/realai-image_*.png`, `Output/audio/`, `Output/iteration_drift_report.json` | many MB | generated UI/audio fixtures — delete |
| `build_latest.log`, `build_latest2.log`, `build_provider.log`, `build_provider_min.log`, `build_ui.log` | ~190 MB | PyInstaller logs — KEEP, move to `legacy/v2-cloud-gui/Output/build_logs/` (build history of `RealAI.exe`, the unified packaged form). |
| `realai.egg-info/` | small | regenerable from `pip install -e .` |
| `realai_knowledge_store.json` | 2.4 KB | 15-row duplicate fixture |

### 1B. Create `legacy/` buckets with API-surface `__init__.py` files

Create three new top-level directories and the following new files:

**`legacy/v0-megamodule/__init__.py`** — re-exports `RealAI`, `RealAIClient`, `PROVIDER_CONFIGS`, `PROVIDER_ENV_VARS`, `ModelCapability`, `CAPABILITIES`, `AGENT_REGISTRY`, `_detect_provider` from the body we move out of `realai/__init__.py`. Single entry point for V0 surface.

**`legacy/v1-llama-cpp/__init__.py`** — re-exports `RealAIAPIHandler`, `run_server`, `main`, `get_model_manager`, `get_llm_engine` from `realai/api_server.py` and `realai/local_models.py`.

**`legacy/v2-cloud-gui/__init__.py`** — re-exports `launch_gui` from `realai_gui.py` and `app` from `main.py`.

Each `__init__.py` carries a docstring declaring "cross-version imports only through this module" — the rule that Phase 2 enforces by grep.

### 1C. Move V0/V1/V2 code to their buckets

Using `git mv` (preserves blame):

**To `legacy/v0-megamodule/`** (the megamodule body, split out of `realai/__init__.py`):
- New file `realai/_v0_compat.py` holds the **entire** body of today's `realai/__init__.py` (10,191 lines: `AgentExecutionStatus`, `AccessProfile`, `AgentDefinition`, `AgentExecution`, `AgentRegistry`, `CloudProvider`, `CloudInstance`, `DistributedTask`, `CloudDeploymentManager`, `DistributedComputingCoordinator`, `LoadBalancer`, `AutoScaler`, `_detect_provider`, `ModelCapability`, `ComputerModeStatus`, `ScreenRegion`, `RecordedAction`, `ScreenCapture`, `MouseKeyboardController`, `WindowManager`, `LearningRecorder`, `ComputerMode`, `CitationEngine`, `RealAI`, `RealAIClient`, `main`).
- `legacy/v0-megamodule/__init__.py` does `from realai._v0_compat import *` so `from realai import RealAIClient` and `from legacy.v0_megamodule import RealAI` both keep working.

**To `legacy/v1-llama-cpp/`**:
- `realai/api_server.py` → `legacy/v1-llama-cpp/api_server.py`
- `realai/local_models.py` → `legacy/v1-llama-cpp/local_models.py`
- `core/` → `legacy/v1-llama-cpp/core/`
- `realai-core/` → `legacy/v1-llama-cpp/realai-core/`
- `agents/` → `legacy/v1-llama-cpp/agents/`
- `autopilot/` → `legacy/v1-llama-cpp/autopilot/`
- `src/` → `legacy/v1-llama-cpp/src/`
- `start_realai_server.bat` → `legacy/v1-llama-cpp/start_realai_server.bat`
- `scripts/setup_local_llama.py` → `legacy/v1-llama-cpp/scripts/setup_local_llama.py`
- `examples/local_llama_example.py` → `legacy/v1-llama-cpp/examples/local_llama_example.py`
- `tests/test_local_llama_integration.py` → `legacy/v1-llama-cpp/tests/test_local_llama_integration.py`
- `models/models/` (registry.json.example) → `legacy/v1-llama-cpp/models/`
- `SETUP_COMPLETE.md` → `legacy/v1-llama-cpp/SETUP_COMPLETE.md`
- V1 docs (`docs/LOCAL_LLAMA_README.md`, `docs/local-llama-setup.md`, `docs/MIGRATION_GUIDE.md`, `docs/IMPLEMENTATION_SUMMARY.md`, `docs/DELIVERABLES.md`, `docs/TRAVIS_README.md`) → `legacy/v1-llama-cpp/docs/`

**To `legacy/v2-cloud-gui/`**:
- `realai_gui.py` → `legacy/v2-cloud-gui/realai_gui.py`
- `api_server.py` (root 4-line shim) → `legacy/v2-cloud-gui/api_server_shim.py`
- `main.py` (root Vercel shim) → `legacy/v2-cloud-gui/vercel_main.py`
- `Output/RealAI-Setup.exe` → `legacy/v2-cloud-gui/Output/RealAI-Setup.exe` (the unified packaged form of RealAI — the "final form" of the V0–V3 evolution; the V2 bucket README documents it as the container for the whole ecosystem)
- `build_latest.log`, `build_latest2.log`, `build_provider.log`, `build_provider_min.log`, `build_ui.log` → `legacy/v2-cloud-gui/Output/build_logs/` (build history of `RealAI.exe`)
- `docs/CAPABILITIES.md`, `docs/QUICKSTART.md`, `docs/CONTRIBUTING.md`, `docs/developer-onboarding.md`, `docs/github_issue_board.md` → `legacy/v2-cloud-gui/docs/`

The root gets fresh 4-line shims: `api_server.py` does `from legacy.v2_cloud_gui.api_server_shim import main, run_server` and `main.py` does `from legacy.v2_cloud_gui.vercel_main import app` (vercel `wsgi_app(environ, start_response)` shim).

### 1D. Refactor `realai/__init__.py` to a 6-line shim

After moving the body to `realai/_v0_compat.py`, replace `realai/__init__.py` with:

```python
"""RealAI canonical entry point. V0 import compatibility is preserved
through realai._v0_compat; new code should import from realai.server,
realai.cli, realai.training, realai.self_builder, or realai.closed_loop.
"""
from realai._v0_compat import *   # noqa: F401,F403
```

This keeps `from realai import RealAIClient, RealAI, PROVIDER_CONFIGS, ModelCapability` working (used by `realai/sdk/__init__.py`, `test_realai.py`, and the `realai:` console script entry in `pyproject.toml`).

The `realai:` console script entry resolves to `realai._v0_compat.main` via `from realai._v0_compat import *` — confirmed by step 2 of verification.

### 1E. Update `.gitignore`

Append (to prevent re-introduction):

```gitignore
# At repo root: any new build / debris that escapes to the canonical surface
build_*.log
repo_tree.txt
repo_tree_clean.txt
repo_tree_filtered.txt
repo_tree_shallow.txt
6.0
=10.4.0
"from fastapi import APIRouter, Requ.txt"
PAGES
copilot-session-*.txt
train_qwen_directml.py
node_modules.disabled/
Output/img_*.png
Output/realai-image_*.png
Output/audio/
Output/iteration_drift_report.json
realai.egg-info/
realai_knowledge_store.json
/training/__init__.py

# legacy/ is exempt: historical .exe + build logs live under legacy/v2-cloud-gui/Output/
# and are intentionally checked in as V2 lineage (the unified packaged form of RealAI).
!legacy/v2-cloud-gui/Output/**/*.exe
!legacy/v2-cloud-gui/Output/**/build_*.log
```

### 1F. Add bucket READMEs and fences

Create three new files:
- `legacy/v0-megamodule/README.md` — "V0 (megamodule seed) — replaced by V3 modular server, kept for lineage."
- `legacy/v1-llama-cpp/README.md` — "V1 (llama.cpp sub-process era) — kept for V1 tests + the `llama-server.exe` 8080-port launcher."
- `legacy/v2-cloud-gui/README.md` — "V2 (cloud router + Tkinter desktop GUI) — kept for users who still want the standalone desktop client. **Contains `Output/RealAI-Setup.exe` (642 MB), the unified packaged form of RealAI — the container for the whole V0–V3 ecosystem, built once and distributed as a single executable.** Build history lives under `Output/build_logs/`."

Create two fence files for non-RealAI siblings:
- `solana-client/README.md` (replace existing) — "External sandbox sibling. Not part of RealAI. See `solana-client/FENCE.txt`."
- `solana-client/FENCE.txt` — `EXTERNAL SANDBOX SIBLING — not part of RealAI.`
- `vendor/README.md` — "Vendored C++ source (llama.cpp). Not built by default; use `vendor/llama.cpp/` directly."

### 1G. Update `realai.toml.example`

Fix `realai.toml.example` so its `model_registry_path` points at `models.yaml` (the V3 live layout) rather than `models/models/registry.json` (which we just moved to `legacy/v1-llama-cpp/models/`).

---

## Phase 2 — Fix cross-imports (only after Phase 1 verifies green)

1. Grep audit for forbidden paths (`legacy.v1_llama_cpp.api_server`, `legacy.v2_cloud_gui.realai_gui`, `from realai_core`, `from core.agents`, etc.) and rewrite any hits to use the bucket root.
2. Add `scripts/check_cross_imports.py` (30-line grep gate) and wire it into `.github/workflows/`.
3. Update `docs/INDEX.md` to point at canonical docs only, with a "Historical lineage" section linking to the three legacy `README.md` files.

Phase 2 is out of scope for the immediate plan. Phase 1 alone gets the user to a clean root with one canonical surface visible from `ls`.

---

## Phase 3 — Unify docs/identity (separate session)

Write `docs/VERSION_LINEAGE.md` and rewrite `docs/STRUCTURE.md` (replacing the planned-state `docs/structure.md`) so that the version timeline and current-state map are one click from `README.md`.

---

## Critical Files

| File | Action | Why |
|---|---|---|
| `realai/__init__.py` | Replace body with 6-line shim | Splits V0 seed from canonical V3 surface |
| `realai/_v0_compat.py` | NEW | Holds the 10,191-line V0 body |
| `realai/api_server.py` → `legacy/v1-llama-cpp/api_server.py` | `git mv` | V1 entry point |
| `realai/local_models.py` → `legacy/v1-llama-cpp/local_models.py` | `git mv` | V1 orphan runtime |
| `api_server.py` (root) → `legacy/v2-cloud-gui/api_server_shim.py` | `git mv` + new 4-line root shim | V2 shim |
| `main.py` (root) → `legacy/v2-cloud-gui/vercel_main.py` | `git mv` + new 4-line root shim | Vercel shim |
| `realai_gui.py` → `legacy/v2-cloud-gui/realai_gui.py` | `git mv` | V2 Tkinter GUI |
| `core/`, `realai-core/`, `agents/`, `autopilot/`, `src/` → `legacy/v1-llama-cpp/` | `git mv` (whole dirs) | V1 orphan TS framework |
| `start_realai_server.bat` → `legacy/v1-llama-cpp/` | `git mv` | V1 8080 launcher |
| `scripts/setup_local_llama.py`, `examples/local_llama_example.py`, `tests/test_local_llama_integration.py` → `legacy/v1-llama-cpp/{scripts,examples,tests}/` | `git mv` | V1 helpers |
| 6 v1 docs → `legacy/v1-llama-cpp/docs/`; 5 v2 docs → `legacy/v2-cloud-gui/docs/` | `git mv` | Lineage docs |
| `realai.toml.example` | edit `model_registry_path` | Fix V3 config example |
| `.gitignore` | append Phase 1 block | Prevent reintroduction of debris |
| `solana-client/README.md` (replace), `solana-client/FENCE.txt` (new), `vendor/README.md` (new) | write | Fence external siblings |
| `legacy/v{0,1,2}/__init__.py` (3 new), `legacy/v{0,1,2}/README.md` (3 new) | write | Bucket API + lineage |

---

## Reusable / Referenced Code

- `realai/server/app.py` — canonical FastAPI entry, must not be touched in Phase 1.
- `realai/server/config.py` — already reads `realai.toml`, `models.yaml`, `providers.yaml`. Phase 1 leaves these files at root unchanged.
- `realai/self_builder.py`, `realai/closed_loop.py`, `realai/auto_improver.py` — V3 self-improvement loop, untouched.
- `realai/training/*` (finetune, pipeline, bootstrap_weights, export_gguf, llama_tools, build_datasets, eval, extract_from_agent_tools) — V3 training pipeline, untouched.
- `start_realai.bat`, `start_self_build.bat` — V3 launchers, untouched.
- `apps/frontend`, `packages/cli`, `packages/sdk-ts`, `providers/realai`, `providers/openai` — V3 TS monorepo, untouched.
- `tests/test_agent_protocol.py`, `test_bootstrap_weights.py`, `test_cli_commands.py`, `test_extract_sessions.py`, `test_model_assets.py`, `test_self_builder.py`, `test_training_tools.py` — V3 tests, untouched.

---

## Verification (after Phase 1)

Run from `C:\Users\tsmit\realai`:

```bash
# 1. Dead debris is gone (each "OK" = deleted)
for f in repo_tree.txt train_qwen_directml.py \
         package-lock.json node_modules.disabled 6.0 '=10.4.0' \
         'from fastapi import APIRouter, Requ.txt' PAGES \
         Output/img_*.png Output/realai-image_*.png Output/audio/; do
  [ -e "$f" ] && echo "FAIL: $f still present" || echo "OK: $f"
done

# 1b. KEEP files have been moved to legacy/v2-cloud-gui/Output/
[ -e legacy/v2-cloud-gui/Output/RealAI-Setup.exe ] && echo "OK: RealAI.exe preserved as V2 lineage" || echo "FAIL: RealAI.exe missing"
ls legacy/v2-cloud-gui/Output/build_logs/ | grep -q build_ && echo "OK: build logs preserved" || echo "FAIL: build logs missing"

# 2. Canonical still boots (all five console scripts resolve)
python -m realai.server.app --help
realai-server --help
realai --help
realai-build --help
realai-loop --help
realai-cli --help

# 3. V0 compat still works (the contract that realai/sdk/__init__.py and test_realai.py depend on)
python -c "from realai import RealAI, RealAIClient, PROVIDER_CONFIGS, ModelCapability; print('OK')"
python -c "from realai import PROVIDER_ENV_VARS, _detect_provider; print('OK')"

# 4. Root shims still resolve to legacy buckets
python api_server.py --help    # imports legacy.v2_cloud_gui.api_server_shim
python main.py                 # imports legacy.v2_cloud_gui.vercel_main (Vercel wsgi_app)

# 5. V0/V1/V2 buckets importable (lineage preserved)
python -c "from legacy.v0_megamodule import RealAIClient, CAPABILITIES; print('OK')"
python -c "from legacy.v1_llama_cpp import run_server, RealAIAPIHandler, get_model_manager; print('OK')"
python -c "from legacy.v2_cloud_gui import launch_gui; print('OK')"

# 6. Canonical training still works
python -c "import realai.training.finetune, realai.training.export_gguf, realai.training.bootstrap_weights; print('OK')"
python -c "import realai.training.pipeline, realai.training.eval, realai.training.build_datasets; print('OK')"
python -c "import realai.training.extract_from_agent_tools, realai.training.llama_tools; print('OK')"

# 7. Tests still pass at the baseline (31/36 with same 2 failed + 3 error as pre-Phase-1)
python -m pytest tests/ -q
# Pre-Phase-1 baseline: 31 passed, 2 failed, 3 error — must match exactly.

# 8. TS monorepo still builds (apps/, packages/, providers/)
pnpm install
pnpm -r --if-present build
pnpm --filter @realai/frontend typecheck

# 9. Visual signal at root — legacy/ should be a directory
ls -d */ | sort
# Expected: apps/  legacy/  models/  packages/  providers/  realai/  tests/
#            checkpoints_lora/  docs/  examples/  scripts/  vendor/  solana-client/  .vscode/  etc.
ls legacy/
# Expected: v0-megamodule/  v1-llama-cpp/  v2-cloud-gui/
```

**Phase 1 success criteria**: All 9 verification steps green. `git status` shows only: file deletes (debris), `git mv` history-preserved moves, three new `legacy/v*/__init__.py`, three new `legacy/v*/README.md`, the new 6-line `realai/__init__.py`, the new `realai/_v0_compat.py`, two new root shims (`api_server.py`, `main.py`), the `.gitignore` extension, three new fence/README files, and the `realai.toml.example` fix. No regressions in the 31/36 test baseline.

---

## What Phase 1 Does NOT Do

- It does not delete the V0/V1/V2 code. Everything is rehomed under `legacy/` with importable surfaces.
- It does not change `realai/server/*`, `realai/training/*`, `realai/self_builder.py`, `realai/closed_loop.py`, `realai/auto_improver.py`, or any V3 module.
- It does not touch `apps/`, `packages/`, `providers/` (the canonical TS monorepo).
- It does not run the self-build loop or fine-tune — those are runtime behaviors, unchanged by the moves.
- It does not write `docs/VERSION_LINEAGE.md` or rewrite `docs/STRUCTURE.md` (Phase 3, separate session).
- It does not fix cross-bucket imports (Phase 2, separate session).
- It does not delete the three "core" Python packages (`realai/`, `core/`, `realai-core/`). `core/` and `realai-core/` are moved to `legacy/v1-llama-cpp/` so the canonical `realai/` is the only Python core at the root.