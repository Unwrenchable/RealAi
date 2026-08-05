# Self-heal cycle report

Started: `2026-07-16T17:59:22.068290+00:00`
Finished: `2026-07-16T17:59:25.585622+00:00`
OK: **False**  Apply promote: **False**
Ability coverage vs technical rundown: **46.0%**

## Steps

- **assemble**: ok=True rc=0
- **promote**: ok=True rc=0
- **ability_learn**: coverage_pct=46.0
- **self_improve_evaluate**: scores `{"ability_coverage_pct": 0.46, "ability_live_count": 7.0, "ability_count": 31.0, "ability_surface_samples": 33.0, "reasoning": 1.0, "coding": 1.0, "safety": 0.8, "tool_use": 1.0, "memory": 1.0, "agent`
- **training_plan**: plan status `ready`
- **verify_matrix**: ok=False rc=1

## Next for human

- Review `scan_results/ability_catalog.json` and `docs/ABILITY_SURFACE.md`
- Review `scan_results/gold_index.md` and `promote_queue.json`
- External roots: `C:\tools\realai`, Users realai trees, historical backups, Atomic Fizz
- Run cycle with apply only when promote list is trusted
- Keep Vulkan :8080 + orchestrator :8001 + UI :3000 healthy
