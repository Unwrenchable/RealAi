# Jump path representation - RackUp SOTD catalogue

**Date:** 2026-09-15  
**For:** roc / Rack_em_up cloud agent  
**Primary bug:** sotd-15 Jump Over the Troublemaker draws as solid 90° zigzag (reads as massé). A **dashed tent** off the CB–OB line (apex `(45, 30.5)`) is also wrong — it still reads as a cloth direction change.

**Related:** Cut-shot **Ghost Ball** contact geometry (imaginary CB center + `contact_point`, not the airborne hop) is in `RACKUP_GHOST_BALL_DIAGRAM_SPEC.md` (derive / `showGhost` default). Cloth swerve is a **smooth curve**, not a zigzag — `RACKUP_MASSE_CURVE_SPEC.md`. Jump maps still use ghost at **post-landing OB contact** — never on the hop.

## Root cause

1. `SotdPathSegment` is only `{ from, to }` - no `style` / `kind`.
2. Jump drills encode the hop as an in-plane kink through `(45, 32)` on an otherwise straight CB→OB line (off-line tent).
3. `ShotMapDiagram` draws **CB→OB as always solid**; only CB-after is dashed. So even a hop apex, if rendered, looks like massé/swerve - not airborne. A dashed tent at `(45, 30.5)` has the same plan-view problem.

## Required semantics

| Segment | style | kind | Meaning |
|---------|-------|------|---------|
| CB → takeoff | solid | ground | rolling approach |
| takeoff → landing (through blocker x/y) | **dashed** | **airborne** | straight hop **over** blocker (overhead) |
| landing → OB contact | solid | ground | land then roll into OB |
| OB → pocket | solid | object | object path |
| CB after contact | dashed | cue_after | (existing) |

**Rule:** `category === "jump"` must never use a solid **or dashed** polyline that tents / zigzags around a blocker in table Y. That shape is reserved for **nothing** — massé / cloth swerve is a **smooth curve** (`RACKUP_MASSE_CURVE_SPEC.md`). Airborne is a **straight** plan-view hop: same x/y as the blocker (overhead), not an angled apex off the CB–OB line.

## Schema patch (types + maps)

```ts
export type SotdPathSegment = {
  from: SotdPoint;
  to: SotdPoint;
  style?: 'solid' | 'dashed'; // default 'solid'
  kind?: 'ground' | 'airborne' | 'object' | 'cue_after';
};
```

Mirror in:
- `rackup-backend/src/realai/v2/sotd-shot-maps.ts`
- `rackup-web/src/lib/types.ts`

## Geometry derive (`shot-map-geometry.ts`)

Extend `DerivedShotGeometry`:

```ts
cueApproach: SotdPoint[];   // solid ground only (CB→takeoff, landing→contact)
cueAirborne: SotdPoint[];   // dashed hop (takeoff→over-blocker→landing), collinear in plan view; [] if not jump
```

For `category === 'jump'`:
- Build `cueAirborne` from segments with `kind==='airborne'` OR `style==='dashed'` before contact.
- Keep `cueApproach` as solid ground pieces only (do not include airborne midpoints in the solid path).
- Airborne points stay **collinear-ish** with the CB–OB line (perp. ≤ 2). The hop goes **straight through/over** the blocker in plan view (overhead). Do **not** synthesize an off-line tent apex. If the blocker is within 2 of the line, `over` may sit at blocker `(x, y)` even when that y disagrees slightly with the interpolated CB–OB y.
- Fallback if maps not yet tagged: detect the **jumped-over blocker ball** (`role: "blocker"`, or the unique object within 2 of the hop) on/near the CB–OB line and synthesize takeoff / over-blocker / landing. Tag `role: "blocker"` on emit.

## Diagram (`ShotMapDiagram.tsx`)

After drawing solid `cueApproach`, draw `cueAirborne` with `solid={false}` (existing dash pattern). Do not draw airborne as part of the solid approach.

## sotd-15 - Jump Over the Troublemaker (REPLACE intended_path)

Keep balls:
- CB `(24, 25.5)`
- blocker #7 `(45, 25.2)`
- OB #1 `(70, 25.2)`
- pocket `(100, 25)`

**Current (broken) path:**
```
(24,25.5)→(45,32)→(70,25)→(100,25)   // all implicit solid → massé zigzag
```

**Do not use** a dashed tent through `(45, 30.5)` — that apex is off the CB–OB line and still reads as a cloth direction change.

**Corrected intended_path** (collinear-ish hop **over** blocker `(45, 25.2)`):
```json
[
  { "from": { "x": 24, "y": 25.5 }, "to": { "x": 39, "y": 25.4 }, "style": "solid", "kind": "ground" },
  { "from": { "x": 39, "y": 25.4 }, "to": { "x": 45, "y": 25.2 }, "style": "dashed", "kind": "airborne" },
  { "from": { "x": 45, "y": 25.2 }, "to": { "x": 51, "y": 25.3 }, "style": "dashed", "kind": "airborne" },
  { "from": { "x": 51, "y": 25.3 }, "to": { "x": 70, "y": 25.2 }, "style": "solid", "kind": "ground" },
  { "from": { "x": 70, "y": 25.2 }, "to": { "x": 100, "y": 25 }, "style": "solid", "kind": "object" }
]
```

ASCII intent: solid to just before #7, **dashed hop straight over #7** (plan-view x/y = blocker), solid into 1, solid to pocket.

## Sibling Jump maps - same massé-shaped clone (FLAG + PATCH)

All four use apex `(45, 32)` solid kink (off-line tent — also fail if only the style is flipped to dashed):

| id | name | cue | blocker | OB | same bug |
|----|------|-----|---------|-----|----------|
| sotd-15 | Jump Over the Troublemaker | (24,25.5) | #7 (45,25.2) | #1 (70,25.2) | YES - fix first |
| sotd-32 | Jump-Draw Hybrid Tease | (23,25) | #7 (46.2,25) | #1 (71.2,25) | YES - same pattern |
| sotd-45 | Elevator Jump Over the Rack Ghost | (24,25.5) | #7 (45,25.6) | #1 (70,25.6) | YES |
| sotd-50 | Venom-Style Jump-Curve Tease | (26,25) | #7 (45,25.4) | #1 (70,25.4) | YES - if truly jump+curve, airborne still dashed; curve after landing only |

Template for siblings (scale takeoff/landing to each blocker.x; **no off-line apex**):
- takeoff.x = blocker.x - 6; y interpolated on the CB–OB line
- landing.x = blocker.x + 6; y interpolated on the CB–OB line
- **over-point precedence** (when they disagree, as on sotd-50: line y ≈ 25.17, blocker y = 25.4):
  1. No tent: every airborne vertex stays within **2** of the CB–OB line (perp. **≤ 2** pass; **> 2** fail).
  2. Cover `blocker.x` on the **contiguous pre-contact airborne span**, inclusive — a vertex at `blocker.x` counts (sotd-15: 39→45 and 45→51). Post-contact / `cue_after` dashes do not count.
  3. If the blocker itself is within **2** of the CB–OB line, place `over` at `(blocker.x, blocker.y)` (overhead). That slack is the “collinear-ish” budget — not a Y tent.
  4. If the blocker is **> 2** off the CB–OB line, keep the hop on the line and still cover `blocker.x`; do not tent toward it. On-line-enough blocker is the prerequisite for “same x/y overhead.”
- Tag the **jumped-over blocker ball** (the obstacle, not the cue) `role: "blocker"`. Infer only if **exactly one** non-primary object (not `role: "object"` / `"prop"` / `"helper"`) lies within **2** of the airborne polyline. If zero or several candidates, require the explicit role (`jump_blocker_ambiguous`).
- ground y ≈ cue / ball line — hop stays collinear-ish, not `cue.y + 5`

## QA flags (catalogue)

1. `category==jump` && any **solid** segment midpoint with `|y - cue.y| >= 4` while x between CB and OB → **massé-shaped jump** (fail) `jump_zigzag`.
2. `category==jump` && the **contiguous pre-contact airborne span** (`kind:airborne` **or** dashed segments **before primary-OB contact**) does not cover `blocker.x` **inclusively** → **missing airborne** (fail). A shared endpoint at `blocker.x` is a pass. Post-contact airborne does not satisfy this.
3. `category==jump` && any airborne vertex perp. distance from the CB–OB line **> 2** (e.g. tent apex `(45, 30.5)` vs line ~25.2) → **airborne tent** (fail) `jump_airborne_tent`. Boundary **= 2** is a pass.
4. `category==jump` && min distance from the airborne polyline to blocker `(x, y)` **> 2**, while the blocker is **≤ 2** from the CB–OB line → **hop misses blocker** (fail) `jump_misses_blocker`. (If the blocker is **> 2** off the line, flag 2 + 3 only — do not require the hop to leave the line.)
5. Combo drills: path must not pass through intervening object balls without contact segment (separate open QA).
6. Diagram remount: key ShotMap by `shot.id` so layers don't stack when switching drills.

## Out of scope for RealAI

Live catalogue draw stays RackUp local maps (`sotd-shot-maps.ts`). RealAI does not draw SOTD at request time.
