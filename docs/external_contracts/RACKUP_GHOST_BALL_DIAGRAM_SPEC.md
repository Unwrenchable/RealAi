# Ghost Ball diagram contract — RackUp SOTD maps

**Date:** 2026-09-14  
**For:** roc / Rack_em_up (Nest + SPA) + RealAI catalogue corrections  
**Related:** `RACKUP_JUMP_PATH_SPEC.md` (airborne stroke; ghost is contact geometry, not the hop)  
**Scope:** Spec + diagram fields only. No Ghost Ball tutorial, site marketing, or instructional UI copy.

When RealAI specifies or fixes shot diagrams, use **Ghost Ball aiming** for contact geometry.

Live catalogue draw stays RackUp (`shot-map-geometry.ts`, `ShotMapDiagram.tsx`). RealAI does not draw SOTD at request time. This file is a schema ping — override fields are **additive**; Nest/SPA already derive ghost when the map omits them.

---

## Coordinate system

Same as SOTD maps / jump spec:

| Axis | Range | Direction |
|------|-------|-----------|
| x | 0–100 | head → foot |
| y | 0–50 | near → far |

Ball **diameter** in map units = **2 ×** object-ball radius in the same units as map coords (typically **~3.4–3.8**). Live cloth `buildTableGeometry` exposes `table.ballRadius`; the diagram draws the ghost circle at that radius. There is no `table-geometry` source in this RealAI repo — treat **map-unit diameter ≈ 3.6** (or `2 × table.ballRadius` in cloth space) unless a map sets `ghost_ball.radius`.

---

## Optional map-level override (`SotdShotMap`)

Catalogue fields. Prefer these when present; else derive as today.

```ts
ghost_ball?: {
  x: number;           // ghost CB center (map units)
  y: number;
  radius?: number;     // map units; default = object ball radius / half diameter
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

## Derived geometry (SPA source of truth when map omits override)

Nest/SPA already compute this in `shot-map-geometry.ts`:

```ts
ghostBall: SotdPoint | null;  // imaginary CB center at contact
showGhost: boolean;
contactPoint: SotdPoint;      // near OB toward cue (touch point)
```

Derivation (geometry only):

```
aimDir        = normalize(aimTarget − OB)   // pocket, or next combo ball
ghostBall     = OB − aimDir * diameter      // behind OB, opposite pocket
contactPoint  = midpoint(ghostBall, OB)     // = OB − aimDir * (diameter / 2)
```

Live `showGhost`: `!isCombo && cutAngle ∈ [12, 78] && !railFirst`.

---

## Aiming rule (geometry only)

1. Aim line: OB center → pocket (or next combo ball).
2. Ghost CB center sits on that line **behind** the OB (opposite pocket), at center-to-center distance = ball diameter.
3. Real CB path aims through ghost center (or to ghost center for stun full-ball).
4. Contact-point marker = midpoint between ghost CB center and OB center (touch point).
5. Prefer map `ghost_ball` when present; else derive as today.
6. Jump / airborne: ghost still applies to **OB contact after landing**; do not put ghost on the airborne apex (`RACKUP_JUMP_PATH_SPEC.md`).
7. Combos: live renderer hides ghost (`showGhost` requires `!isCombo`). If a map forces `ghost_ball.show: true`, ghost is first OB → second ball (same diameter rule). Default remains hide.

---

## Draw contract (RackUp owns local draw)

- Translucent cue-ball fill at `geo.ghostBall` (or map `ghost_ball`), same radius as the live CB (`table.ballRadius`, or `ghost_ball.radius` when set).
- Dashed or low-alpha stroke.
- Optional tiny contact tick/dot at `contact_point` / `contactPoint`.
- Never add instructional paragraphs in the UI from this spec.

---

## When RealAI corrects catalogue maps

Include `ghost_ball` (+ optional `contact_point`) for **cut shots** that need aim clarity — not only path polylines.

Do not emit ghost for:

- rail-first shots (live `!railFirst`)
- combo maps unless explicitly forcing first-OB → second-ball aim (`ghost_ball.show: true`)
- the airborne apex of a jump (ghost belongs at post-landing OB contact)

---

## Out of scope for RealAI

No Rack_em_up code in this PR. roc wires Nest/SPA types + optional override read. Live derive stays the default when fields are omitted.
