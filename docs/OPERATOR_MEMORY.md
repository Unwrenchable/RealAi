OPERATOR MEMORY:
- REALAI_HOME = C:\RealAI-clean (product home). Branch: live/realai-clean-20260911.
- Hive gold: realai/orchestration/v3_orchestrator.py. Bridge gold: realai/orchestration/v3_runtime_bridge.py.
- Edit gold, not shims. Keep package-root dest-empty shims.
- One product tree. No v1/v2/v3 dirs. No mega-merge.
- Coach is not a learned plugin. Learned plugins use {slug}_learned. Never edit rackup_coach or atomicfizz_coach.
- Fusion UI is product-root fusion-ui/. No Fusion tab in Console.
- Console gold: apps/vscode/webview/console.html (sync product-root console.html).
- AFC and RackUp are HTTP clients to :8001 only. GET /v1/agents stays ~14 hive roles.
