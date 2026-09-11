# Exportable orchestrators

| File | Live wiring |
|------|-------------|
| `orchestrator_router.py` | `realai.server.*` imports |
| `orchestrator_orchestration.py` | self-contained TaskOrchestrator |
| `orchestrator_self_improvement.py` | mostly stdlib |
| `orchestrator_overmind_runner.py` | `realai.engine.executor.AgentExecutor` |
| `orchestrator_solana.py` | `ToolDefinition` from plugins/agent_tools |

Dispatch via: `abilities.nest_orchestrators` (`action=run nest=...`).
