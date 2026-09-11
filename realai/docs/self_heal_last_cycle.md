# Self-heal cycle report

Started: `2026-08-27T16:01:37.422954+00:00`
Finished: `2026-08-27T16:01:43.731099+00:00`
OK: **True**  Apply promote: **True**
Ability coverage vs technical rundown: **47.2%**

## Steps

- **assemble**: ok=True rc=0
- **promote**: ok=True rc=None
- **promote_gold_queue**: ok=True rc=0
- **ability_learn**: coverage_pct=47.2
- **self_improve_evaluate**: scores `{"reasoning": 1.0, "coding": 1.0, "safety": 0.8, "tool_use": 1.0, "memory": 1.0, "agent": 0.0, "overall": 0.8}`
- **training_plan**: plan status `ready`

## Next for human

- Review `scan_results/ability_catalog.json` and `docs/ABILITY_SURFACE.md`
- Review `scan_results/gold_index.md` and `promote_queue.json`
- External roots: `C:\tools\realai`, Users realai trees, historical backups, Atomic Fizz
- Run cycle with apply only when promote list is trusted
- Keep Vulkan :8080 + orchestrator :8001 + UI :3000 healthy
- Do not run full dds3 multi-day scans
