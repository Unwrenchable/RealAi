# Apps map (inventory 2026-09-21)

Live product UI and extension live at **product root**. Nested copies under `realai/` are twin dumps — do not treat as gold. Do not park in this pass (read-only inventory).

| Path | Role | Action | Why |
|------|------|--------|-----|
| `frontend/` | Canonical Next UI (`realai-frontend` 0.1.0) | **KEEP** | Full tree (`app/`, `components/`, `.next`); noted as gold in `apps/FRONTEND_PARKED_NOTE.md` |
| `apps/vscode/` | Live VS Code / Cursor Console extension | **KEEP** | `realai-vscode` **1.2.15** with `package.json`, `src/`, `webview/` |
| `apps/api/` | Local API helpers | **KEEP** | Small Python surface (`main.py`, `routes/`) |
| `apps/fusion-ui/` | Static fusion twin | **PARKED** phase 3 | `_quarantine/twins_20260926/apps__fusion-ui`. Product-root `fusion-ui/` is what `:8001` serves |
| `apps/dashboard/` | Dashboard package stub | **SHIM** | `@realai/dashboard` 0.1.0; sparse; confirm before delete |
| `apps/frontend/` | Former nested frontend | **PARKED** phase 3 | `_quarantine/twins_20260926/apps__frontend`. Authority is `frontend/` |
| `apps/` (root) | App container | **KEEP** | Holds vscode/api; child `frontend/` and `fusion-ui/` twins are shelved |
| `realai/apps/` | Nest twin of `apps/` | **PARKED** phase 3 | `_quarantine/twins_20260926/realai__apps` (incomplete `vscode/`, no `package.json`) |
| `realai/apps/vscode/` | Incomplete vscode nest | **PARKED** phase 3 | Moved with `realai/apps/`. Live extension stays `apps/vscode/` |
| `realai/realai-frontend/` | Thin frontend dump | **PARKED** phase 2 | `_quarantine/twins_20260926/realai__realai-frontend/` |

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
