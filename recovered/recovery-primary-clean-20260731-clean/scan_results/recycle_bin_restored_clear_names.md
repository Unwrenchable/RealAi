# Restored from Recycle Bin — clear names

Generated: `2026-07-15T14:43:38.804509+00:00`

## Why names looked confusing

In Recycle Bin, Windows renames deleted files to:

- `$I....` = metadata (original path)
- `$R....` = the actual file

Those **$R** names are useless by themselves. This folder restores copies using **original paths/names**.

## Where things are

Root of this restore:

`/mnt/c/realai/recovered/from_recycle_bin/restored_clear_names`

### Important finds
- Model configs: search for `models.yaml`, `registry.json.txt`
- Code shims: `api_server.py`, `config.py`
- Large archive: look for `realai-core.tar.gz.part-aa/ab/ac` and `ASSEMBLED_realai-core.tar.gz` if assembled
- Deleted folders: `*.DIR_NOTE.json` explain how to fully Restore in Explorer

### Stats
- Restored files: **30**
- Restored bytes: **5,016,227,255**
- Dir notes: **12**
- Missing payload (metadata only): **10**
- Secrets skipped: **3**
- Errors: **0**

## Do NOT open secrets into git

Secrets found in Recycle Bin were **not** restored here. Handle wallet/env files outside the repo.

## Full inventory

See `RESTORE_MAP.json` in this folder and `scan_results/recycle_bin_gold_map.json`.


# Restore map (clear names)

Output: `/mnt/c/realai/recovered/from_recycle_bin/restored_clear_names`

| Original path | Restored as | Size |
|---|---|---|
| `C:\Users\tsmit\realai-clean\realai-core.tar.gz.part-ab` | `Users/tsmit/realai-clean/realai-core.tar.gz.part-ab` | 2097152000 |
| `C:\Users\tsmit\realai-clean\realai-core.tar.gz.part-aa` | `Users/tsmit/realai-clean/realai-core.tar.gz.part-aa` | 2097152000 |
| `C:\Users\tsmit\realai-clean\realai-core.tar.gz.part-ac` | `Users/tsmit/realai-clean/realai-core.tar.gz.part-ac` | 821370880 |
| `C:\Users\tsmit\overseer-bot-ai\.env.txt` | `Users/tsmit/overseer-bot-ai/.env.txt` | 1843 |
| `C:\Users\tsmit\models\registry.json.txt` | `Users/tsmit/models/registry.json.txt` | 1195 |
| `C:\Users\tsmit\realai\api_server.py` | `Users/tsmit/realai/api_server.py` | 571 |
| `C:\Users\tsmit\realai\config.py` | `Users/tsmit/realai/config.py` | 432 |
| `C:\Users\tsmit\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS-main\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS-main\scripts\realai.js` | `Users/tsmit/ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS-main/ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS-main/scripts/realai.js` | 404 |
| `C:\Users\tsmit\AppData\Roaming\RealAi\config\models.yaml` | `Users/tsmit/AppData/Roaming/RealAi/config/models.yaml` | 300 |
| `C:\Users\tsmit\realai\realai\models\models.yaml` | `Users/tsmit/realai/realai/models/models.yaml` | 219 |
| `C:\Users\tsmit\realai\PAGES` | `Users/tsmit/realai/PAGES` | 3 |
| `\\?\C:\Users\tsmit\realai\realai\│├── .vscode\│   ├── settings.json│   ├── launch.json│   ├── tasks.json│   └── extensions.json│├── src\│   ├── index.ts│   ├── core\│   │   ├── logger.ts│   │   ├── config.ts│   │   └── errors.ts│   ││   ├── agents\│   │   ├── base-agent.ts│   │   ├── overseer-agent.ts│   │   └── image-agent.ts│   ││   ├── mcp\│   │   ├── server.ts│   │   ├── tools\│   │   │   ├── filesystem.ts│   │   │   ├── search.ts│   │   │   └── python-runner.ts│   │   └── schemas\│   │       ├── request.ts│   │       └── response.ts│   ││   └── utils\│       ├── paths.ts│       ├── env.ts│       └── types.ts│├── python\│   ├── scripts\│   │   ├── train.py│   │   ├── embed.py│   │   └── doctor.py│   ││   └── notebooks\│       └── exploration.ipynb│├── tests\│   ├── test_agents.py│   ├── test_api.py│   └── test_memory.py│├── models\├── snapshots\├── docs\│   └── architecture.md│├── .gitignore├── package.json├── pnpm-lock.yaml├── tsconfig.json├── pyproject.toml├── README.md│├── bootstrap.ps1├── scaffold.ps1└── install.ps1` | `_weird_paths/_._._._-_._._._._._._._` | 0 |
| `C:\Users\tsmit\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS-main\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS-main\public\js\overseer\realai.js.txt` | `Users/tsmit/ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS-main/ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS-main/public/js/overseer/realai.js.txt` | 0 |
| `C:\Users\tsmit\overseer-bot-ui` (folder) | `Users/tsmit/overseer-bot-ui.DIR_NOTE.json` | note |
| `C:\Users\tsmit\realai\pnpm-lock.yaml` | `Users/tsmit/realai/pnpm-lock.yaml` | 208088 |
| `C:\Users\tsmit\realai\apps\vscode\images\realai-icon.svg` | `Users/tsmit/realai/apps/vscode/images/realai-icon.svg` | 111838 |
| `C:\Python314\Scripts\realai.exe` | `Python314/Scripts/realai.exe` | 108312 |
| `C:\Users\tsmit\realai\copilot-session-39a9656a-48d7-4b7a-8ad4-aa82a2c153ee.7z` | `Users/tsmit/realai/copilot-session-39a9656a-48d7-4b7a-8ad4-aa82a2c153ee.7z` | 79116 |
| `C:\Users\tsmit\realai\apps\frontend\pnpm-lock.yaml` | `Users/tsmit/realai/apps/frontend/pnpm-lock.yaml` | 18091 |
| `C:\Users\tsmit\realai\package-lock.json` | `Users/tsmit/realai/package-lock.json` | 15285 |
| `C:\Users\tsmit\realai\tsconfig.json.disabled` | `Users/tsmit/realai/tsconfig.json.disabled` | 1142 |
| `C:\Users\tsmit\.realai\local_models.json` | `Users/tsmit/.realai/local_models.json` | 671 |
| `C:\Users\tsmit\RealAIProject\.env.local.txt` | `Users/tsmit/RealAIProject/.env.local.txt` | 606 |
| `C:\Users\tsmit\agent-tools\agent-tools-main\agents\router.agent.json.txt` | `Users/tsmit/agent-tools/agent-tools-main/agents/router.agent.json.txt` | 163 |
| `C:\Program Files\RealAI` (folder) | `Program Files/RealAI.DIR_NOTE.json` | note |
| `C:\Users\tsmit\realai` (folder) | `Users/tsmit/realai.DIR_NOTE.json` | note |
| `C:\Users\tsmit\realai\New Python.File.py` | `Users/tsmit/realai/New Python.File.py` | 0 |
| `C:\Users\tsmit\realai\realai\│├── .vscode` (folder) | `_weird_paths/_._.DIR_NOTE.json` | note |
| `C:\Users\tsmit\realai\New Python Script.py` | `Users/tsmit/realai/New Python Script.py` | 0 |
| `C:\Users\tsmit\ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS-main\scripts` (folder) | `Users/tsmit/ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS-main/scripts.DIR_NOTE.json` | note |
| `C:\Users\tsmit\realai\__init__.py` | `Users/tsmit/realai/__init__.py` | 0 |
| `C:\Python314\Lib\site-packages\realai-2.0.0.dist-info` (folder) | `Python314/Lib/site-packages/realai-2.0.0.dist-info.DIR_NOTE.json` | note |
| `C:\Users\tsmit\realai\history` (folder) | `Users/tsmit/realai/history.DIR_NOTE.json` | note |
| `C:\ProgramData\Microsoft\Windows\Start Menu\Programs\RealAI` (folder) | `ProgramData/Microsoft/Windows/Start Menu/Programs/RealAI.DIR_NOTE.json` | note |
| `C:\Users\tsmit\realai\.sixth` (folder) | `Users/tsmit/realai/.sixth.DIR_NOTE.json` | note |
| `C:\llama\models` (folder) | `llama/models.DIR_NOTE.json` | note |
| `C:\Users\tsmit\realai\.py` | `Users/tsmit/realai/.py` | 0 |
| `C:\Users\tsmit\realai\.continue\.continue` (folder) | `Users/tsmit/realai/.continue/.continue.DIR_NOTE.json` | note |
| `C:\Users\tsmit\.grok\worktrees\tsmit-realai\realai - Copy\New Python Script.py` | `Users/tsmit/.grok/worktrees/tsmit-realai/realai - Copy/New Python Script.py` | 0 |
| `C:\Users\tsmit\.grok\worktrees\tsmit-realai\realai - Copy\New Text Document.txt` | `Users/tsmit/.grok/worktrees/tsmit-realai/realai - Copy/New Text Document.txt` | 0 |
| `C:\Users\tsmit\realai\backend` (folder) | `Users/tsmit/realai/backend.DIR_NOTE.json` | note |
| `C:\Users\tsmit\realai\.continue` | `Users/tsmit/realai/.continue` | 4096 |
| (assembled from parts aa+ab+ac) | `ASSEMBLED_realai-core.tar.gz` | 5015674880 |