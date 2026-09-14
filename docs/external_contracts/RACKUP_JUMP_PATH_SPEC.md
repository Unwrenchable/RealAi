# RackUp Jump Path Spec

**Document version:** 1.0.0  
**Date:** 2026-09-14  
**Status:** LOCKED — Shot Map / SOTD jump hop rendering  
**Audience:** RealAI orch (map authors) + RackUp Nest / web (geometry + SVG)  
**Related:** `REALAI_RACKUP_WIRING_CONTRACT.md` (ability envelopes), `RACKUP_GAME_KNOWLEDGE_AND_AI_CONTRACT.md` (`shot_of_the_day`)  
**Implemented in RackUp:** [PR #35](https://github.com/Unwrenchable/Rack_em_up/pull/35)

---

## 0. Rule (non-negotiable)

Jump hops **must** render as **dashed airborne cue arcs** over the blocker.

A **solid cloth zigzag** through a blocker at mid-air height is **wrong**. That read is a massé, not a jump.

```
WRONG  solid polyline CB → (blocker.x, cue.y+~7) → object   (massé zigzag)
RIGHT  solid ground to takeoff → dashed arc over blocker → solid landing → object
```

---

## 1. Path segment contract

`intended_path` is an array of segments. Optional fields replace the old `airborne?: boolean`.

| Field | Type | Default / meaning |
|-------|------|-------------------|
| `from`, `to` | `{ x, y }` | Cloth coords (`x` 0–100, `y` 0–50) |
| `style` | `solid` \| `dashed` | omit = `solid` |
| `kind` | `ground` \| `airborne` \| `object` \| `cue_after` | omit = `ground` |

```ts
type SotdPathStyle = 'solid' | 'dashed';
type SotdPathKind = 'ground' | 'airborne' | 'object' | 'cue_after';

type SotdPathSegment = {
  from: { x: number; y: number };
  to: { x: number; y: number };
  style?: SotdPathStyle;
  kind?: SotdPathKind;
};
```

**Airborne test (either is enough):** `kind === 'airborne' || style === 'dashed'`.

| `kind` | Stroke | Role |
|--------|--------|------|
| `ground` | solid | Cloth run (CB → takeoff, landing → object) |
| `airborne` | **dashed** | Hop over blocker (takeoff → apex → landing) |
| `object` | solid | Object ball → pocket (or next combo ball) |
| `cue_after` | solid | Cue after impact |

---

## 2. Geometry (Nest + web must derive)

Owners: `sotd-shot-maps.ts` (catalogue), `shot-map-geometry.ts` / `sotd-shot-map-geometry.ts` (derive), `ShotMapDiagram.tsx` (SVG).

From `intended_path`, derive — **do not** chord takeoff → landing as one solid line through the blocker:

| Field | Contents |
|-------|----------|
| `cueApproach` | **Ground-only** CB → takeoff |
| `cueAirborne` | **Dashed** takeoff → apex → landing (empty if no hop) |
| `cueApproachAfter` | Solid cloth landing → object (empty if no split) |
| `objectPath` | Pocketing ball → pocket |
| `cueAfter` | CB after impact |

Renderer: `cueAirborne` with `solid={false}` (dashed). Never draw a solid polyline that includes the airborne apex.

**Clone pattern** (when only cue + blocker are known):

| Vertex | Formula |
|--------|---------|
| takeoff | `(blocker.x - 6, cloth y)` |
| apex | `(blocker.x, cue.y + 5)` |
| landing | `(blocker.x + 6, cloth y)` |

Path: solid takeoff run → **dashed** takeoff → apex → landing → solid to object → solid object to pocket.

---

## 3. Canonical hop — Jump Over the Troublemaker (`sotd-15`)

| Ball | Role | Coord |
|------|------|-------|
| CB | cue | `24, 25.5` |
| #7 | blocker | `45, 25.2` |
| #1 | object | `70, 25.2` |
| pocket | target | `100, 25` |

```
solid  ground    (24, 25.5) → (39, 25.4)
dashed airborne  (39, 25.4) → (45, 30.5) → (51, 25.4)
solid  ground    (51, 25.4) → (70, 25.2)
solid  object    (70, 25.2) → (100, 25)
```

Sibling maps (`sotd-32`, `sotd-45`, `sotd-50`) use the same takeoff / apex / landing clone.

---

## 4. Validator (Nest client)

| Code | Fail when |
|------|-----------|
| `jump_needs_airborne` | Jump category and no segment with `kind === 'airborne'` or `style === 'dashed'` |
| `jump_zigzag` | Ground (non-airborne) vertices bend through a blocker like a massé. **Ignore airborne vertices** — the apex bend *is* the hop |

Jump maps **may** target a cloth-edge rail (e.g. `100,25` on sotd-15). Non-jump mid-rail pockets still fail.

Older maps without `style`/`kind`: if `category === 'jump'` and a cloth segment passes within ~3.6 of a `role: 'blocker'`, annotate that segment `style: 'dashed'`, `kind: 'airborne'`.

---

## 5. Nest / RealAI expectations

- Catalogue + Coach diagrams consume this shape from local maps **or** RealAI `shot_of_the_day` payloads that include `intended_path`.
- Ability envelopes stay in `REALAI_RACKUP_WIRING_CONTRACT.md`. This file only locks **path stroke + hop geometry**.
- Do not emit a single solid polyline CB → mid-air apex → object.

---

## 6. RackUp file map (PR #35)

| File | Owns |
|------|------|
| `rackup-backend/src/realai/v2/sotd-shot-maps.ts` | Catalogue paths (sotd-15 / 32 / 45 / 50) |
| `rackup-backend/src/realai/v2/sotd-shot-map-geometry.ts` | Server-side derive + validator |
| `rackup-backend/src/realai/v2/dto/sotd-map.dto.ts` | Segment DTO (`style`, `kind`) |
| `rackup-web/src/lib/shot-map-geometry.ts` | Client derive (`cueAirborne`) |
| `rackup-web/src/components/ShotMapDiagram.tsx` | Dashed airborne stroke |
| `rackup-web/src/lib/types.ts` | `SotdPathSegment` |
