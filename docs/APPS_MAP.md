# Apps map (inventory 2026-09-21)

Live product UI and extension live at **product root**. Nested copies under `realai/` are twin dumps — do not treat as gold. Do not park in this pass (read-only inventory).

| Path | Role | Action | Why |
|------|------|--------|-----|
| `frontend/` | Canonical Next UI (`realai-frontend` 0.1.0) | **KEEP** | Full tree (`app/`, `components/`, `.next`); noted as gold in `apps/FRONTEND_PARKED_NOTE.md` |
| `apps/vscode/` | Live VS Code / Cursor Console extension | **KEEP** | `realai-vscode` **1.2.15** with `package.json`, `src/`, `webview/` |
| `apps/api/` | Local API helpers | **KEEP** | Small Python surface (`main.py`, `routes/`) |
| `apps/fusion-ui/` | Static fusion UI | **KEEP** | Tiny HTML/JS; not a nest dump |
| `apps/dashboard/` | Dashboard package stub | **SHIM** | `@realai/dashboard` 0.1.0; sparse; confirm before delete |
| `apps/frontend/` | Former nested frontend | **PARK** (later) | Explicitly parked by note; slim vs root `frontend/` |
| `apps/` (root) | App container | **KEEP** | Holds vscode/api/fusion; child `frontend/` is the parked one |
| `realai/apps/` | Nest twin of `apps/` | **PARK** (later) | Parallel tree (~24k files); different `__init__.py`; extra `desktop/`/`widget/` |
| `realai/apps/vscode/` | Incomplete vscode nest | **PARK** (later) | No `package.json`; subset of live extension |
| `realai/realai-frontend/` | Thin frontend dump | **PARK** (later) | 6 files only; package.json ≠ root `frontend/` |

## Organs (related)

| Item | Value |
|------|--------|
| Authority | `modules/organs` |
| Import | `from modules.organs import hive_status` |
| `realai.modules.organs` | Resolves to same package when `PYTHONPATH` includes product root (alias, not a second tree) |
| `hive_status` | `organ_count` 45, `expected` 44, `complete` True |

## Runtime (probe)

- `:8001` health + `/v1/models` — up (existing stack; not started by this pass)
- `:8080` Vulkan health — up
