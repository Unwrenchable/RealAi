# RealAI Provider-Level Status (unification/ultimate-all)

RealAI is a **full local-first OpenAI-compatible provider**, not a thin wrapper.
External providers (Grok, OpenAI, …) are optional adapters only.

## Living branch
- Branch: `unification/ultimate-all`
- See `git log -1` for current SHA (batch1 `6871a473`, batch2+promote `7d003b4e`, organs pass follows).

## Living stack (present)
| Area | Location |
|------|----------|
| Agent runtime | `realai/agent_runtime.py`, `core/agents/*` |
| API / inference | `realai/api_server.py`, `realai/server/*`, `core/inference/*` |
| Router | `realai/router.py` |
| Models | `core/models/*`, `models/` |
| Memory | `realai/memory/engine.py`, `core/memory/*` (+ long_term_engine) |
| Training | `core/training/*`, `modules/training/datasets/*` |
| Orchestration | `core/orchestration/*` |
| Tools / plugins | `core/tools/*`, `realai/tools.py`, `plugin_marketplace.py` |
| Voice / web3 | `core/voice/*`, `core/web3/*` |
| Self-improvement | `realai/self_improvement.py` |
| **44 synthetic organs** | `modules/organs/*` via `modules.organs.hive` / `adapters.organs` |
| Registry | `registry/modules.yaml` |
| Snapshots | `recovered/<slug>/` (32+ branch tips) |

## Organs hive
```python
from modules.organs import hive_status, call_organ
hive_status()  # organ_count == 44
call_organ("organ.hippocampus", goal="encode episode")
```

## Gaps / next
- Remaining remote recovery/* not yet under recovered/ (batch3)
- Deeper organ→runtime wiring (each hook fully bound)
- Chat-only reconstructions should land only as organ modules (done for 44)
