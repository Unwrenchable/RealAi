# Ghost Ball diagram contract — RackUp SOTD maps

**Date:** 2026-09-15  
**For:** roc / Rack_em_up (Nest + SPA) + RealAI catalogue corrections  
**Related:** `RACKUP_JUMP_PATH_SPEC.md` (airborne stroke; ghost is contact geometry, not the hop), `RACKUP_MASSE_CURVE_SPEC.md` (cloth swerve is a smooth curve, not a tent)  
**Scope:** Spec + diagram fields only. No Ghost Ball tutorial, site marketing, or instructional UI copy.

When RealAI specifies or fixes shot diagrams, use **Ghost Ball aiming** for contact geometry.

**Primary path is always automatic:** Nest/SPA `deriveShotGeometry` / `showGhost`. Map `ghost_ball` / `contact_point` are **rare pins only**, not the catalogue default.

Live catalogue draw stays RackUp (`shot-map-geometry.ts`, `ShotMapDiagram.tsx`). RealAI does not draw SOTD at request time. This file is a schema ping — override fields are **additive and rare**; Nest/SPA already derive ghost when the map omits them (the common case).

---

## Coordinate system

Same as SOTD maps / jump spec:

| Axis | Range | Direction |
|------|-------|-----------|
| x | 0–100 | head → foot |
| y | 0–50 | near → far |

Live ghost **offset diameter** in map units is pinned:

```ts
const diameter = 4.4; // deriveShotGeometry
```

Use **4.4** for Ghost Ball center-to-center offset (OB → ghost CB). This is the live SPA `deriveShotGeometry` pin — **not** the physical ball diameter **2.25** used for cloth/lane clearance in the walkthrough. Do not substitute 2.25, ~3.4–3.8, or `2 × table.ballRadius` for the offset. A map may still set `ghost_ball.radius` for the **drawn** circle only.

---

## Rare map-level pin (`SotdShotMap`) — not the default

`SotdShotMap` today has **no** `ghost_ball` field. The fields below are **additive**. Catalogue maps **omit** them and let the SPA derive. Emit a pin **only** when live derive would be wrong (wrong aim target, combo first-OB pin, or a known derive bug). When a pin is present, the renderer prefers it.

```ts
ghost_ball?: {
  x: number;           // ghost CB center (map units)
  y: number;
  radius?: number;     // map units; omit = SVG ballR (cloth ballRadius); not 4.4/2
  show?: boolean;      // force show/hide; omit = renderer derives showGhost
};
contact_point?: {      // optional explicit CB–OB contact marker on OB surface
  x: number;
  y: number;
};
```

Mirror in:

- `rackup-backend/src/realai/v2/sotd-shot-maps.ts`
- `rackup-web/src/lib/types.ts`

---

## Derived geometry (SPA source of truth — the default)

Nest/SPA already compute this in `shot-map-geometry.ts`:

```ts
ghostBall: SotdPoint | null;  // imaginary CB center at contact
showGhost: boolean;
contactPoint: SotdPoint;      // near OB toward cue (touch point)
```

Live pin (`deriveShotGeometry`):

```ts
const diameter = 4.4;
ghostBall = OB - normalize(aimTarget - OB) * 4.4;
// aimTarget = pocket (or next combo ball)
```

`contactPoint` stays the touch point near the OB toward the cue (midpoint of ghost CB center and OB center).

Live show:

```ts
showGhost = !isCombo && cut > 12 && cut < 78 && !railFirst;
```

---

## Aiming rule (geometry only)

1. Aim line: OB center → pocket (or next combo ball).
2. Ghost CB center sits on that line **behind** the OB (opposite pocket), at center-to-center distance = **4.4** map units.
3. Real CB path aims through ghost center (or to ghost center for stun full-ball).
4. Contact-point marker = midpoint between ghost CB center and OB center (touch point).
5. **Default:** derive (`showGhost`). Map `ghost_ball` / `contact_point` are rare pins — emit only when derive would be wrong. When a pin is present, prefer it.
6. Jump / airborne: ghost still applies to **OB contact after landing**; do not put ghost on the airborne hop (`RACKUP_JUMP_PATH_SPEC.md`). The hop is collinear over the blocker in plan view — not an apex pin for ghost.
7. Combos: live renderer hides ghost (`showGhost` requires `!isCombo`). A forced `ghost_ball.show: true` is a rare pin (first OB → second ball, same **4.4** offset). Default remains hide.

---

## Draw contract (RackUp owns local draw)

Live `ShotMapDiagram` at `geo.ghostBall` (or map `ghost_ball`):

- Stroke: dashed, `rgba(255,255,255,0.5)`
- Radius: SVG `ballR` (cloth `ballRadius`)
- Fill: none
- Optional tiny contact tick/dot at `contact_point` / `contactPoint`
- Map `ghost_ball.radius` overrides draw radius only when present
- Never add instructional paragraphs in the UI from this spec

---

## When RealAI corrects catalogue maps

**Prefer auto.** Omit `ghost_ball` and `contact_point` on corrections so Nest/SPA derive / `showGhost` run. Do **not** stamp overrides onto every cut “for aim clarity.”

Emit a map-level pin **only** when derive would be wrong. That is the exception, not the catalogue default.

Do not emit ghost for:

- rail-first shots (live `!railFirst`)
- combo maps unless a rare first-OB → second-ball pin is required (`ghost_ball.show: true`)
- the airborne hop of a jump (ghost belongs at post-landing OB contact; hop is straight over the blocker, not an apex)

---

## Out of scope for RealAI

No Rack_em_up code in this PR. roc wires Nest/SPA types + optional rare-pin read. Live derive / `showGhost` stays the default when fields are omitted.
