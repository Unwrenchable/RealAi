# RealAI Console (VS Code)

The **same console aesthetic** as `console.html` — local hive chat + full ability/tool dock — inside VS Code.

## Install

```powershell
cd apps\vscode
npm run compile
npm run package
code --install-extension .\realai-vscode-1.2.0.vsix --force
```

Reload the window.

## Open it

- Command Palette → **RealAI: Open Console** (`Ctrl+Shift+A`)
- Or activity bar **RealAI → Ultimate Hub → Open Console**

## Layout

| Column | What |
|--------|------|
| Left rail | Threads, `/phase` `/patches` `/repo`, hive live pill |
| Center | Console feed + composer (operator chips) |
| Right dock | **Abilities / Tools / Agents** from live Hive catalog — click to run or insert |

## Stack

Talks to Hive `http://127.0.0.1:8001` (Vulkan `:8080`). Start with `START_HERE.bat` / `start_all.bat`.

**v1.2.4 — browser console parity:** same Hive chat path as http://127.0.0.1:8001/console (tools + voice on, speak-aloud, thread messages without stage spam). Command **RealAI: Open Browser Console** opens the Hive `/console` in your browser.
