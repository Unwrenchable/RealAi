# RealAI Import Boundary (2026-09-19)

The directory `realai/realai/` was a duplicate, non-Git package mirror inside
the live product tree. The workspace has one Git root at `C:\RealAI-clean`;
there was no nested `.git` directory.

The duplicate mirror was moved, without deletion, to the ignored recovery
archive at `recovered/realai-import-20260919/`.

## Merge decision

The live product-level implementations remain authoritative. The overlapping
inner files were older or reduced copies of the live files, including:

- `realai/api_server.py`
- `realai/tools.py`
- `realai/v3_orchestrator.py`
- `realai/server/app.py`
- `realai/server/tools_runtime.py`

The live package imports successfully after the move, including the API server,
tool registry, and v3 orchestrator entry points. The archived copy remains
available for targeted comparison if a future change identifies a behavior not
already present in the live implementation.

Generated dependencies, caches, model weights, and recovery snapshots remain
outside the product source boundary and are not promoted automatically.