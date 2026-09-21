# RealAI agent + module contract

This is the RealAI contract. Root `AGENTS.md` on live is a foreign Grok App Builder file and is not this product.

## You are assisting RealAI, one intelligence

- Modular but unified. Isolated packages, one hive.
- Explicit paths. No hidden magic.
- Disposable modules. Swap a plugin without breaking orchestration.
- Multi-provider. Hive routes; Vulkan is the local default.
- v1 / v2 / v3 are layers, not forks.

## Where code goes

| Add this | Put it here |
|----------|-------------|
| Hive / routing / multi-agent | `realai/orchestration/` |
| Engine primitive (memory, safety, identity) | `realai/core/` |
| HTTP surface | `realai/server/` or `realai/api/` |
| Plugin | `realai/plugins/<name>/` |
| Ability handler | `abilities/<name>.py` + catalog row |
| Organ | `modules/organs/<system>/` |
| CLI command | `realai/cli/` |
| VS Code UI | `apps/vscode/` |
| Web UI | `frontend/` + `packages/design-system` |
| Scanner / promote tool | `scanners/` |
| Recovered dump | `_quarantine/` or a `recovery/*` branch |

## Do not

- Create `v1/`, `v2/`, `v4/` trees.
- Vendor RackUp into this repo.
- Mega-merge recovery branches.
- Put GGUF weights in git.
- Edit dest-empty shims — edit the gold they re-export.

## Runtime entry

```text
python -m realai.v3_orchestrator --host 127.0.0.1 --port 8001
```
