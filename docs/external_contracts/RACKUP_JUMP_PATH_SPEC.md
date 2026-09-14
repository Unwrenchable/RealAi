# Jump path representation - RackUp SOTD catalogue

**Date:** 2026-09-13  
**For:** roc / Rack_em_up cloud agent  
**Primary bug:** sotd-15 Jump Over the Troublemaker draws as solid 90° zigzag (reads as massé)

## Root cause

1. `SotdPathSegment` is only `{ from, to }` - no `style` / `kind`.
2. Jump drills encode the hop as an in-plane kink through `(45, 32)` on an otherwise straight CB→OB line.
3. `ShotMapDiagram` draws **CB→OB as always solid**; only CB-after is dashed. So even a hop apex, if rendered, looks like massé/swerve - not airborne.

## Required semantics

| Segment | style | kind | Meaning |
|---------|-------|------|---------|
| CB → takeoff | solid | ground | rolling approach |
| takeoff → landing (via optional apex) | **dashed** | **airborne** | jump over blocker |
| landing → OB contact | solid | ground | land then roll into OB |
| OB → pocket | solid | object | object path |
| CB after contact | dashed | cue_after | (existing) |

**Rule:** `category === "jump"` must never use a solid polyline that arcs around a blocker in table Y. That shape is reserved for `masse` / swerve.

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
cueAirborne: SotdPoint[];   // dashed hop (takeoff→apex→landing); [] if not jump
```

For `category === 'jump'`:
- Build `cueAirborne` from segments with `kind==='airborne'` OR `style==='dashed'` before contact.
- Keep `cueApproach` as solid ground pieces only (do not include airborne midpoints in the solid path).
- Fallback if maps not yet tagged: detect blocker on CB-OB line and synthesize takeoff/apex/landing (same coords as below).

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

**Corrected intended_path:**
```json
[
  { "from": { "x": 24, "y": 25.5 }, "to": { "x": 39, "y": 25.4 }, "style": "solid", "kind": "ground" },
  { "from": { "x": 39, "y": 25.4 }, "to": { "x": 45, "y": 30.5 }, "style": "dashed", "kind": "airborne" },
  { "from": { "x": 45, "y": 30.5 }, "to": { "x": 51, "y": 25.4 }, "style": "dashed", "kind": "airborne" },
  { "from": { "x": 51, "y": 25.4 }, "to": { "x": 70, "y": 25.2 }, "style": "solid", "kind": "ground" },
  { "from": { "x": 70, "y": 25.2 }, "to": { "x": 100, "y": 25 }, "style": "solid", "kind": "object" }
]
```

ASCII intent: solid to just before X, **dashed hop over X**, solid into 1, solid to pocket.

## Sibling Jump maps - same massé-shaped clone (FLAG + PATCH)

All four use apex `(45, 32)` solid kink:

| id | name | cue | blocker | OB | same bug |
|----|------|-----|---------|-----|----------|
| sotd-15 | Jump Over the Troublemaker | (24,25.5) | #7 (45,25.2) | #1 (70,25.2) | YES - fix first |
| sotd-32 | Jump-Draw Hybrid Tease | (23,25) | #7 (46.2,25) | #1 (71.2,25) | YES - same pattern |
| sotd-45 | Elevator Jump Over the Rack Ghost | (24,25.5) | #7 (45,25.6) | #1 (70,25.6) | YES |
| sotd-50 | Venom-Style Jump-Curve Tease | (26,25) | #7 (45,25.4) | #1 (70,25.4) | YES - if truly jump+curve, airborne still dashed; curve after landing only |

Template for siblings (scale takeoff/landing to each blocker.x):
- takeoff.x = blocker.x - 6
- apex = (blocker.x, cue.y + 5)
- landing.x = blocker.x + 6
- y on ground ≈ cue.y / ball line

## QA flags (catalogue)

1. `category==jump` && any solid segment midpoint with `|y - cue.y| >= 4` while x between CB and OB → **massé-shaped jump** (fail).
2. `category==jump` && no `kind:airborne` / `style:dashed` segment crossing blocker.x → **missing airborne** (fail).
3. Combo drills: path must not pass through intervening object balls without contact segment (separate open QA).
4. Diagram remount: key ShotMap by `shot.id` so layers don't stack when switching drills.

## Out of scope for RealAI

Live catalogue draw stays RackUp local maps (`sotd-shot-maps.ts`). RealAI does not draw SOTD at request time.
