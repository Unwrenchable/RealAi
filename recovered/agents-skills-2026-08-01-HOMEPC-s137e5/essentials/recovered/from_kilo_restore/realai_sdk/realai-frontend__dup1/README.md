# Recovered agent_tools (gap recovery)

Generated: `2026-07-14T15:36:35.266330+00:00`

## Sources

- Historical pyc: `C:\Users\tsmit\realai_historical_backups\realai_versions_20260612\agent-tools-main\agent-tools-main\agent_tools\__pycache__`
- SOURCES blueprint: `C:\Users\tsmit\realai\agent-tools\agent-tools-main\agent_tools.egg-info\SOURCES.txt`
- Hollow live tree: `C:\\Users\\tsmit\\realai\\agent-tools\\agent-tools-main`

## Status

- Decompile attempts: 8
- Scaffold modules: 8

Full original module list (from SOURCES.txt):

```
README.md
pyproject.toml
agent_tools/__init__.py
agent_tools/cli.py
agent_tools/dashboard.py
agent_tools/executor.py
agent_tools/importer.py
agent_tools/models.py
agent_tools/registry.py
agent_tools/runtime.py
agent_tools.egg-info/PKG-INFO
agent_tools.egg-info/SOURCES.txt
agent_tools.egg-info/dependency_links.txt
agent_tools.egg-info/entry_points.txt
agent_tools.egg-info/requires.txt
agent_tools.egg-info/top_level.txt
agent_tools/data/access_profiles.json
agent_tools/data/agents.json
agent_tools/engine/__init__.py
agent_tools/engine/executor.py
agent_tools/engine/loader.py
agent_tools/engine/logger.py
agent_tools/engine/memory.py
agent_tools/engine/router.py
agent_tools/engine/test_harness.py
agent_tools/providers/__init__.py
agent_tools/providers/anthropic.py
agent_tools/providers/groq.py
agent_tools/providers/local.py
agent_tools/providers/openai.py
agent_tools/providers/realai.py
agent_tools/providers/router.py
agent_tools/tooling/__init__.py
agent_tools/tooling/crypto.py
agent_tools/tooling/filesystem.py
agent_tools/tooling/http.py
agent_tools/tooling/registry.py
agent_tools/tooling/solana.py
tests/test_dashboard.py
tests/test_hardening.py
tests/test_orchestration.py
tests/test_registry.py
```

Next: decompile remaining modules, recover engine/providers/tooling from git history,
then promote into `C:\\realai\\agent_tools` when complete enough.
