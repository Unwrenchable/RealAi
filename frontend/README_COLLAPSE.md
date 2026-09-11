# Canonical frontend (UI collapse 2026-09-08)

## Canonical path

Product-root frontend\ is the single Next.js 15 App Router UI.

- Source copied from gold apps\frontend (Next 15.5.21)
- Design system path: file:../packages/design-system
- API base default: http://127.0.0.1:8001

## How to run

1. Start Vulkan + hive orchestrator so ports 8080 and 8001 are up.
2. From product root, use start_ui.bat (enters frontend\).
3. Or enter frontend\, set REALAI_API_BASE and NEXT_PUBLIC_API_URL to the 8001 URL, install packages, then use the package.json dev script.
4. Open http://127.0.0.1:3000

## Fusion legacy

- fusion-ui remains for asset serving; do not delete.
- See fusion-ui\FUSION_LEGACY.md
- Console and fusion remain on orchestrator port 8001.

## Parked copies

See _quarantine\_parked\2026-09-08-ui-collapse\
