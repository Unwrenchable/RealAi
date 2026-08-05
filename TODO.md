# 🔥 Unified RealAI Server — Full Repository Unification TODO

## Phase 1 — Core Unification (In Progress)

### Active Execution Checklist (Current Run)
- [x] Read/unify baseline server/UI files for Phase 1 scope
- [x] Run baseline pytest sweep and collect failures
- [ ] Fix CLI regressions (`extract-data`, `doctor`, `repo-loop`, top-level `main(argv)`)
- [ ] Run Fusion UI browser interaction matrix (A-E)
- [ ] Validate backend 400/error path matrix end-to-end
- [ ] Regenerate `tools.md` and `skills.md` from unified sources
- [ ] Re-run full pytest after fixes
- [ ] Produce final phase report + categorized issues + completion status

### 1) Repository Walk & Source Extraction
- [x] Walk main server sources
  - [x] `realai/api_server.py`
  - [x] `realai_server.py`
  - [x] `realai/server/app.py`
  - [x] `realai/server/router.py`
  - [x] `realai/server/tools_runtime.py`
- [x] Walk capability & manifest sources
  - [x] `docs/CAPABILITIES.md`
  - [x] `docs/model-manifest.md`
  - [x] `manifest.json`
  - [x] `schema/tool.schema.json`
  - [x] `realai/tools.py`
- [ ] Walk ARCHIVE (deep extraction deferred to Phase 2)
  - [ ] old server implementations
  - [ ] agent orchestration logic
  - [ ] memory systems
  - [ ] tool runners
  - [ ] prompt/skill patterns
  - [ ] older routing logic
  - [ ] older error handling
  - [ ] older JSON schemas
  - [ ] any full chat pipelines
  - [ ] any full embeddings/tasks pipelines
  - [ ] any full model/provider registries

### 2) Unified Server Architecture Design
- [x] Fusion-UI-first server behavior present
  - [x] `/` serves `fusion-ui/index.html`
  - [x] static asset serving from `fusion-ui/`
  - [ ] explicit `/static/*` mount path parity (to finalize)
- [x] Core API endpoints present
  - [x] `GET /health`
  - [x] `GET /v1/models`
  - [x] `GET /v1/providers`
  - [x] `POST /v1/chat/completions`
  - [x] `POST /v1/embeddings` (minimal)
  - [x] `POST /v1/tasks` (minimal)
- [ ] Harden chat/input validation matrix
  - [ ] invalid JSON -> 400
  - [ ] invalid messages type -> 400
  - [ ] missing model/messages policy finalized
  - [ ] valid shape -> deterministic stub fallback
- [x] Deterministic clean-branch stub fallback present
  - [x] content: `Hello from RealAI stub`
- [ ] Archive-derived hooks deferred to Phase 2
  - [ ] agent hooks
  - [ ] memory hooks
  - [ ] tool invocation hooks
  - [ ] older error-handling patterns

### 3) Entrypoint Unification
- [x] `realai_server.py` is authoritative launcher baseline
- [x] Add `REALAI_USE_STRUCTURED=1` optional gating path
- [ ] Confirm no accidental auto-boot from structured/archive paths
- [ ] Confirm port 8000 ownership process guidance

### 4) Fusion UI Integration
- [x] Patch `fusion-ui/index.html`
  - [x] add required DOM IDs (`chat-log`, `chat-input`, `chat-form`, `backend-error-banner`, `health-indicator`)
  - [x] add `request-viewer` placeholder
- [x] Patch `fusion-ui/script.js`
  - [x] endpoint alignment check
  - [x] 400 error display refinement
  - [x] health indicator wiring
  - [x] chat append flow verification

### 5) Tools & Skills Unification Docs
- [ ] Regenerate `tools.md` from:
  - [ ] `schema/tool.schema.json`
  - [ ] `realai/tools.py`
  - [ ] `realai/server/tools_runtime.py`
  - [ ] archive tool runners (Phase 2 extension)
- [ ] Regenerate `skills.md` from:
  - [ ] `docs/CAPABILITIES.md`
  - [ ] `docs/model-manifest.md`
  - [ ] archive prompt/agent/memory patterns (Phase 2 extension)
- [ ] Normalize naming/schema/safety/registry/runtime notes

### 6) Backend Testing Matrix
- [ ] Happy paths
  - [ ] `/`
  - [ ] `/script.js`
  - [ ] `/health`
  - [ ] `/v1/models`
  - [ ] `/v1/providers`
  - [ ] `/v1/chat/completions`
  - [ ] `/v1/embeddings`
  - [ ] `/v1/tasks`
- [ ] Error paths
  - [ ] invalid JSON
  - [ ] invalid messages
  - [ ] missing fields
  - [ ] wrong types
  - [ ] invalid model policy path
- [ ] Llama/backend isolation checks
  - [ ] llama stays backend-only
  - [ ] no llama auto-boot interference

### 7) Web UI Testing Matrix
- [ ] send chat
- [ ] verify assistant response append
- [ ] verify DOM updates
- [ ] verify no blocking JS errors
- [ ] console sweep
  - [ ] no missing DOM IDs
  - [ ] no fetch errors
  - [ ] no CORS issues
  - [ ] no undefined variables

### 8) Final Verification & Cleanup
- [ ] unified server authoritative
- [ ] structured endpoints work
- [ ] Fusion UI works
- [ ] `tools.md` and `skills.md` accurate
- [ ] archive logic integration summary (Phase 2)
- [ ] no llama server interference
- [ ] error handling correctness
- [ ] schema compatibility with OpenAI/Fusion expectations
- [ ] repo clean and unified

---

## Phase 2 — Archive Deep Extraction (Planned)
- [ ] Deep walk all archive clusters and extract “gold”
- [ ] Integrate safe server/agent/memory/tool improvements
- [ ] Produce integrated-vs-deferred archive summary

## Phase 3 — VS Code Extension + VSIX Alignment (Planned)
- [ ] Walk extension sources (`package.json`, `extension.ts`, commands/providers/client/webview)
- [ ] Align extension base URL/endpoints/schemas/error handling
- [ ] Align webview DOM + health status with unified server
- [ ] Regenerate/build VSIX notes and validation steps
