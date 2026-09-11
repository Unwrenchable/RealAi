# RealAI Unification (`unification/ultimate-all`)

## Goal
Zero development lost + one living unified system.

## Layout
- `core/` — strongest living implementations
- `modules/` — promoted packages that are not core primitives
- `adapters/` — glue so recovered modules talk to core
- `registry/` — discovery map (`modules.yaml`)
- `recovered/<slug>/` — full snapshots of important branches (never delete)

## Rules
- Every valuable branch is archived under `recovered/`
- Promote strongest versions into `core/` / `modules/`
- Wire via adapters + registry
- Do not linear-merge 60 histories
- Do not delete recovered snapshots
