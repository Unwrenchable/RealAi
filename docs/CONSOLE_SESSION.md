# Console session (2026-09-21)

Fix pass against live hive. Did **not** rewrite `console.html`. Did **not** install from `realai/apps/vscode` nest.

## Runtime

| check | result |
|-------|--------|
| hive_health `:8001/health` | **200** ok (`realai-v3-orchestrator`, vulkan ok) |
| vulkan_health `:8080/health` | **200** `{"status":"ok"}` |
| browser `/console` | **Y** — HTML 200 (`http://127.0.0.1:8001/console`) |
| `/v1/tools` | 200 |
| `/v1/agents` | 200 |

Stack was already up; did not start a second orchestrator. Did not start :3000/:5173/:8890.

## Extension build

| item | result |
|------|--------|
| `apps/vscode/out/extension.js` | **yes** (recompiled 2026-09-21) |
| `apps/vscode/webview/console.html` | **yes** (sync-webview from product-root `console.html`) |
| compile failure (before fix) | `Error: Cannot find module 'C:\RealAI-clean\apps\typescript\bin\tsc'` |
| root cause | Broken local shims `apps/vscode/tsc.cmd` / `tsc.js` / `tsc.ps1` pointed at missing `apps\typescript\...` |
| fix | Removed broken shims; `package.json` scripts `compile`/`watch` now call `node ./node_modules/typescript/lib/tsc.js -p ./` |
| vsix | `apps/vscode/realai-vscode-1.2.15.vsix` packaged from **this** tree |
| installed into | Cursor **and** VS Code via `--install-extension ... --force` |

## Host / engines

| host | version | engines.vscode | notes |
|------|---------|----------------|-------|
| Cursor | 3.20.17 | `^1.104.0` | VSIX installed successfully — **no engines downgrade** |
| VS Code | 1.138.0 | `^1.104.0` | Compatible (≥ 1.104) |

## Workspace settings (product home)

Created/updated `C:\RealAI-clean\.vscode\settings.json`:

```json
{
  "realai.baseUrl": "http://127.0.0.1:8001",
  "realai.productHome": "C:\\RealAI-clean",
  "realai.model": "realai-hive"
}
```

## GUI smoke command

Command id: **`realai.consoleSmoke`**  
Title: RealAI: Console Smoke (abilities/tools/agents)  
Also: `realai.openBrowserConsole` → Hive `/console`

Could not click UI from this pass; browser `/console` smoke is green via HTTP.

## Error text (captured)

```
Error: Cannot find module 'C:\RealAI-clean\apps\typescript\bin\tsc'
code: 'MODULE_NOT_FOUND'
```

(during `npm run compile` / bare `tsc` before shim removal)

Extension Host logs on disk were stale (Cursor 2026-09-13) or pre-install (Code 2026-09-21 04:27); no fresh post-install activation stack captured without a GUI reload. After reload, expect activation of `unwrenchable.realai-vscode@1.2.15`.

## Classification

| class | applies? |
|-------|----------|
| hive-down | No (was up) |
| missing `out/extension.js` | No (present; refreshed) |
| compile broken | **Yes** — fixed |
| wrong baseUrl | **Yes** — settings created |
| host engines incompatible | No |
| console.html rewrite needed | No |

## Refused

- No quarantine / recovery merges
- No nest install from `realai/apps/vscode`
- No engines bump
- No `console.html` rewrite
- No extra UI ports
