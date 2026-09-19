# Nest orchestrators (exportable index)

These modules live under `scripts/exportable/` because they use relative
imports from old package layouts. **Do not blind-copy** into this folder.

Adapt into `core/orchestration/` or wrap with an explicit import path after review.

| File | Path |
|------|------|
| `orchestrator_orchestration.py` | `scripts/exportable/orchestrator_orchestration.py` |
| `orchestrator_overmind_runner.py` | `scripts/exportable/orchestrator_overmind_runner.py` |
| `orchestrator_router.py` | `scripts/exportable/orchestrator_router.py` |
| `orchestrator_self_improvement.py` | `scripts/exportable/orchestrator_self_improvement.py` |
| `orchestrator_solana.py` | `scripts/exportable/orchestrator_solana.py` |
