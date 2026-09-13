# RealAI Console UI

Drop these files onto `C:\RealAI-clean`.

## Instant preview (no build)

Open `console.html` in a browser. It talks to `http://127.0.0.1:8000/v1/chat/completions` if the RealAI API is up. If not, it still runs as a local demo so you can judge the UX.

## Next.js drop-in (`apps/frontend`)

1. Replace `src/app/globals.css` with `next/globals.css`
2. Swap `src/app/layout.tsx` title/fonts with `next/layout.tsx`
3. Keep existing `page.tsx` logic — the new CSS restyles the current shell
4. Optional: copy `next/shell-extras.css` and import it from layout

## Design system

- Ink: `#07070b`
- Rail: `#0c0c12`
- Acid: `#d6ff3f`
- Hot: `#ff4d2e`
- Ice: `#7af0ff`
- Type: Geist / ui-sans + IBM Plex Mono for chrome
- Motion: 120–180ms, no bounce, no gradients-for-gradients
