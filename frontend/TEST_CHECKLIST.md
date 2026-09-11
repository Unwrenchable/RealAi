# UI collapse user test checklist (2026-09-08)

frontend node_modules was missing; agent skipped install and did not start servers.

## Static keys verified under frontend
- app/layout.tsx
- app/page.tsx
- components/ChatArena.tsx
- lib/realai.ts

## User steps from product root
1. Enter frontend directory.
2. Install JS dependencies with your package manager.
3. Execute the typecheck script from package.json.
4. Execute the build script from package.json.
5. Bring up Vulkan 8080 and orchestrator 8001.
6. Launch the UI launcher script at product root (cds into frontend).
7. Open http://127.0.0.1:3000
8. Confirm console and fusion still respond on http://127.0.0.1:8001

Env defaults: REALAI_API_BASE and NEXT_PUBLIC_API_URL = http://127.0.0.1:8001
