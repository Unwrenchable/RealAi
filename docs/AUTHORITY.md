# Authority map

Single answers. If two files disagree, this table wins.

| Question | Answer |
|----------|--------|
| What branch do we run? | `live/realai-clean-20260911` |
| What is `main`? | Older unified dump. Archive. Not the hive. |
| What are `recovery/*` and `local/*`? | Snapshot / protect libraries. Diff source only. |
| What is product home? | `C:\\RealAI-clean` (`REALAI_HOME`) |
| What is the Python package? | `C:\\RealAI-clean\\realai` (`import realai`) |
| Where is hive gold? | `realai/orchestration/v3_orchestrator.py` (~153 KB) |
| Where is bridge gold? | `realai/orchestration/v3_runtime_bridge.py` (~81 KB) |
| Where are plugins? | `realai/plugins` |
| Where are organs? | `modules/organs` |
| Where is the honesty map? | `realai/ability_catalog.py` |
| Where are weights? | Local disks only. Never git. |
| Where is quarantine data? | `D:\\RealAI-archive\\_quarantine` (git path is a pointer) |
| Where is the gold shelf? | `C:\\RealAI-gold` |
| Do we keep v1 and v2 folders? | No. Their modules live inside the live package. |
| May we merge all 66 branches? | No. |
