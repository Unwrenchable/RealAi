# RealAI → RackUp SOTD new-entry schema

**Date:** 2026-09-15  
**For:** roc / Rack_em_up Nest ingest + RealAI emitters  
**Status:** Ingest contract **1.0** — JSON only  
**Walkthrough:** `RACKUP_SOTD_GENERATION_WALKTHROUGH.md`  
**Geometry:** `RACKUP_JUMP_PATH_SPEC.md`, `RACKUP_GHOST_BALL_DIAGRAM_SPEC.md`, `RACKUP_MASSE_CURVE_SPEC.md`

RealAI emits this envelope. RackUp merges into Nest modules. Draw stays RackUp-owned.

Live Nest pins (do not drift):

| Module | Export |
|--------|--------|
| `rackup-backend/src/realai/v2/sotd-shot-maps.ts` | `SotdShotMap`, `SOTD_SHOT_MAPS` |
| `rackup-backend/src/shots/shot-catalog.ts` | `CatalogShot`, `SHOT_CATALOG` |

---

## 0. Envelope (propose / ingest)

```json
{
  "schema_version": "1.0",
  "map": { },
  "catalog": { },
  "validation": { "ok": true, "flags": [] }
}
```

```ts
export type SotdProposeEnvelope = {
  schema_version: '1.0';
  map: SotdShotMap;       // §1 — required geometry
  catalog: CatalogShot;   // §2 — required coach tip object
  validation: SotdValidation; // §3
};
```

| Field | Required | Notes |
|-------|----------|--------|
| `schema_version` | yes | Literal `"1.0"` |
| `map` | yes | `SotdShotMap` |
| `catalog` | yes | `CatalogShot`; **`catalog.id === map.id`** |
| `validation` | yes | Merge only when `ok === true` |

Reject the envelope if ids diverge, `schema_version` ≠ `"1.0"`, or `validation.ok` is false.

---

## 1. `map` — `SotdShotMap`

Cloth plane: **x 0–100** head → foot, **y 0–50** near → far. Units: normalized table percent (9-foot aspect 2:1). Same as jump + ghost specs.

### 1.1 Types (Nest + ingest extensions)

```ts
export type SotdPoint = { x: number; y: number };

export type SotdObjectBall = SotdPoint & {
  ballId: number;
  role?: 'object' | 'blocker' | 'prop' | 'helper';
};

export type SotdPathStyle = 'solid' | 'dashed';
export type SotdPathKind = 'ground' | 'airborne' | 'object' | 'cue_after';

export type SotdPathSegment = {
  from: SotdPoint;
  to: SotdPoint;
  style?: SotdPathStyle; // default 'solid'
  kind?: SotdPathKind;
};

export type SotdEnglish = {
  tip_zone: string;
  sidespin: number;
  backspin: number;
  follow: number;
  label: string;
};

export type SotdLandingZone = SotdPoint & { label: string };

/** Nest live maps use 'catalogue' | 'realai'. Ingest envelope uses the pair below. */
export type SotdIngestSource = 'realai' | 'catalog_fallback';
export type SotdMapSource = 'catalogue' | 'realai'; // Nest SOTD_SHOT_MAPS

export type SotdGhostBall = {
  x: number;
  y: number;
  radius?: number; // draw radius only; omit = SVG ballR. Not 4.4/2.
  show?: boolean;  // omit = renderer derives showGhost
};

export type SotdShotMap = {
  id: string;
  name: string;
  difficulty: string;
  difficulty_rating: number;
  category: string;
  speed_category: string;
  tip_zone: string;
  cue_ball_start: SotdPoint;
  object_ball_positions: SotdObjectBall[];
  intended_path: SotdPathSegment[];
  english: SotdEnglish;
  landing_zones: SotdLandingZone[];
  pocket_target: SotdPoint;
  coordinate_system: { x: string; y: string; units: string };
  source: SotdIngestSource; // envelope; see §1.3 for Nest mapping
  ascii_table?: string;     // optional short; Nest live field is string
  ghost_ball?: SotdGhostBall;     // rare pin — Ghost Ball spec; omit = SPA derive
  contact_point?: SotdPoint;      // rare pin — OB surface touch; omit = derive
};
```

`ghost_ball` / `contact_point` are **not** on live `SotdShotMap` today. They are additive **rare pins** per `RACKUP_GHOST_BALL_DIAGRAM_SPEC.md` — catalogue default is omit + SPA `showGhost`. roc mirrors them in Nest + `rackup-web/src/lib/types.ts` when ingesting.

### 1.2 Required vs optional

**Required**

| Field | Type / constraint |
|-------|-------------------|
| `id` | `sotd-NN` (zero-pad) or a new unique id |
| `name` | non-empty |
| `difficulty` | `Easy` \| `Medium` \| `Hard` \| `Insane` (same as `CatalogShot`) |
| `difficulty_rating` | number (live catalog uses 1–4) |
| `category` | `bank` \| `combo` \| `curve` \| `jump` \| `masse` \| `kick` \| `carom` \| `novelty` \| `position` |
| `speed_category` | string; live values include `feather` \| `soft` \| `medium` \| `firm` \| `power` |
| `tip_zone` | clock-face string; **same set** as `CatalogShot.tipZone` (§2) |
| `cue_ball_start` | `{x,y}` on cloth |
| `object_ball_positions` | array; each `{ ballId, x, y, role? }` |
| `intended_path` | array; each `{ from, to, style?, kind? }` |
| `english` | `{ tip_zone, sidespin, backspin, follow, label }` |
| `landing_zones` | array of `{x,y,label}` (e.g. `pocket`, `cb_rest`) |
| `pocket_target` | `{x,y}` required on live Nest. Near a table pocket when a pocket-bearing object leg exists; on **carom** without that leg, a diagram / CB-or-second-ball target (§1.4) |
| `coordinate_system` | see pin below |
| `source` | `"realai"` \| `"catalog_fallback"` |

**Optional**

| Field | When |
|-------|------|
| `ascii_table` | Short legend OK; omit allowed on ingest |
| `ghost_ball` | **Rare pin only** — emit when SPA derive / `showGhost` would be **wrong**. Cuts 12–78° otherwise omit; offset if pinned **4.4** |
| `contact_point` | **Rare pin** — explicit CB–OB touch; omit = midpoint derive |
| `intended_path[].style` / `kind` | Required in practice for **jump** (airborne dashed) and for the pocket-bearing **`kind: "object"`** leg when a pocket is claimed |

Pinned `coordinate_system` (copy this unless the table aspect changes):

```json
{
  "x": "0=head rail → 100=foot rail",
  "y": "0=bottom long rail → 50=top long rail",
  "units": "normalized table percent (9-foot aspect 2:1)"
}
```

### 1.3 `source` mapping

| Envelope `map.source` | Meaning | Nest `SotdMapSource` after merge |
|-----------------------|---------|----------------------------------|
| `realai` | New or RealAI-authored geometry | `"realai"` |
| `catalog_fallback` | Audited / corrected copy of a live catalogue id | `"catalogue"` |

Do not write `"catalog_fallback"` into `sotd-shot-maps.ts` as a raw string until Nest widens `SotdMapSource`. roc maps it on ingest.

### 1.4 `intended_path` rules (geometry, not draw)

- Segments must chain: `to` of *n* ≈ `from` of *n+1* (gap ≤ 1.6).
- Jump: dashed `airborne` **straight through/over** the blocker plan-view `(x, y)`; never a solid or dashed tent / zigzag — `RACKUP_JUMP_PATH_SPEC.md`.
- Curve / massé: **smooth curve** (dense samples or renderer curve), not a polyline tent; **do not** use `kind: "airborne"` for cloth swerve — `RACKUP_MASSE_CURVE_SPEC.md`.
- Object-leg selection: last `kind: "object"`. **Non-carom fallback only:** else last `.to` within 8 of `pocket_target`. Caroms: only an explicit `kind: "object"` pocket leg (walkthrough §3.5).
- `pocket_target` stays required (live Nest). Near-pocket checks apply when an object-leg exists. On **carom** without that leg, it is the diagram / CB-or-second-ball target — skip `path_misses_pocket`, `pocket_not_near`, and `pocket_unmakeable`.
- `pocket_unmakeable` is **one driven primary OB** (deterministic selection in walkthrough §3.5; exclude blocker/prop/helper). Outgoing ray from the **OB center** plus **incoming segment/ray** from the ghost side. Banks / combos / caroms: category flags. Kicks: **only** a direct object pot after contact gets the outgoing-ray check; no ghost check on the rail-before-OB cue path.

### 1.5 Example `map` (cut, auto-derived ghost; no map pin)

```json
{
  "id": "sotd-26",
  "name": "Side-Pocket Soft Cut",
  "difficulty": "Medium",
  "difficulty_rating": 2,
  "category": "position",
  "speed_category": "soft",
  "tip_zone": "center",
  "cue_ball_start": { "x": 40, "y": 18 },
  "object_ball_positions": [
    { "ballId": 1, "x": 50, "y": 12, "role": "object" }
  ],
  "intended_path": [
    { "from": { "x": 40, "y": 18 }, "to": { "x": 50, "y": 12 }, "style": "solid", "kind": "ground" },
    { "from": { "x": 50, "y": 12 }, "to": { "x": 50, "y": 0 }, "style": "solid", "kind": "object" }
  ],
  "english": {
    "tip_zone": "center",
    "sidespin": 0,
    "backspin": 0,
    "follow": 0,
    "label": "none"
  },
  "landing_zones": [
    { "x": 50, "y": 0, "label": "pocket" },
    { "x": 42, "y": 16, "label": "cb_rest" }
  ],
  "pocket_target": { "x": 50, "y": 0 },
  "coordinate_system": {
    "x": "0=head rail → 100=foot rail",
    "y": "0=bottom long rail → 50=top long rail",
    "units": "normalized table percent (9-foot aspect 2:1)"
  },
  "source": "catalog_fallback",
  "ascii_table": "C → 1 → side-near. Legend: C=cue 1=object O=pocket"
}
```

No `ghost_ball` / `contact_point` — SPA derive / `showGhost` is the default (`ghostBall = OB - normalize(aimTarget - OB) * 4.4`). A rare pin (only when that derive would be wrong) looks like `"ghost_ball": { "x": 50, "y": 16.4, "show": true }` plus optional `contact_point`.

---

## 2. `catalog` — `CatalogShot`

Parallel coach-tip object. Fields match Nest `shot-catalog.ts` (`CatalogShot`). **No** Ghost Ball tutorial / marketing paragraphs — setup, stroke, mistakes, success only.

```ts
export type TipZone =
  | 'center'
  | '12-high'
  | '6-low'
  | '3-right'
  | '9-left'
  | '1:30-high-right'
  | '10:30-high-left'
  | '4:30-low-right'
  | '7:30-low-left';

export type StrokeSpeed = 'feather' | 'soft' | 'medium' | 'firm' | 'power';

export type ShotDifficulty = 'Easy' | 'Medium' | 'Hard' | 'Insane';

export type ShotCategory =
  | 'bank'
  | 'combo'
  | 'curve'
  | 'jump'
  | 'masse'
  | 'kick'
  | 'carom'
  | 'novelty'
  | 'position';

export type CatalogShot = {
  id: string;
  name: string;
  tagline: string;
  difficulty: ShotDifficulty;
  category: ShotCategory;
  table: string;
  setup: string[];
  objectBall: string;
  pocket: string;
  tipZone: TipZone;
  tipDetail: string;
  english: string;
  elevation: string;
  speed: StrokeSpeed;
  speedDetail: string;
  bridge: string;
  steps: string[];
  tips: string[];
  commonMistakes: string[];
  successLooksLike: string;
};
```

### 2.1 Required catalog fields

Every field on `CatalogShot` is required for ingest (Nest has no optionals). Walkthrough highlights the tip payload:

| Field | Role |
|-------|------|
| `id` | Same as `map.id` |
| `name` | Same as `map.name` (or documented rename) |
| `tagline` | One line; skill, not slogan farm |
| `difficulty` | Same enum as `map.difficulty` |
| `category` | Same as `map.category` |
| `table` | Short layout (e.g. `9-foot, object ball mid-rail`) |
| `setup` | Bullet list of CB / OB / target |
| `objectBall` | Which ball to treat as object |
| `pocket` | Called pocket in words |
| `tipZone` | Must match `map.tip_zone` |
| `tipDetail` | Where on the CB |
| `english` | Spin in words (`None.`, `Inside right.`, …) |
| `elevation` | Cue angle |
| `speed` | Enum; should agree with `map.speed_category` |
| `speedDetail` | Why that speed |
| `bridge` | Bridge type |
| `steps` | Ordered stroke |
| `tips` | Coaching extras |
| `commonMistakes` | Fail modes |
| `successLooksLike` | Observable make |

`map.english` is numeric spin; `catalog.english` is a sentence. Keep them consistent (zero sidespin ↔ `"None."`).

### 2.2 Example `catalog` (truncated)

```json
{
  "id": "sotd-26",
  "name": "Side-Pocket Soft Cut",
  "tagline": "Soft cut into the side with a quiet cue ball",
  "difficulty": "Medium",
  "category": "position",
  "table": "9-foot, side-pocket cut",
  "setup": [
    "Object ball above the side pocket, half-ball cut.",
    "Cue ball one diamond off, slightly below the aim line."
  ],
  "objectBall": "Any solid (treat as 1-ball)",
  "pocket": "Near side pocket",
  "tipZone": "center",
  "tipDetail": "Dead center — let the cut do the work.",
  "english": "None.",
  "elevation": "Level cue.",
  "speed": "soft",
  "speedDetail": "Soft enough to hold the cut without throwing the ball long.",
  "bridge": "Open bridge, still lower body.",
  "steps": [
    "See the ghost: CB center through the imaginary ball behind the 1.",
    "Pause, then a short smooth stroke.",
    "Stay down until the 1 reaches the pocket."
  ],
  "tips": ["If it under-cuts, the aim line is too thick — move the ghost, not the tip."],
  "commonMistakes": ["Helping the cut with inside english and throwing it off."],
  "successLooksLike": "1 drops center-side; CB dies in the landing zone."
}
```

`steps` may mention “ghost” as **aim geometry** (CB center through the imaginary ball). Do not paste a Ghost Ball tutorial or site hero copy.

---

## 3. `validation`

```ts
export type SotdValidationFlag = {
  code: string;
  pass: boolean;
  message?: string;
};

export type SotdValidation = {
  ok: boolean;
  flags: SotdValidationFlag[] | string[];
};
```

`ok` is true **iff** every makeability flag in the walkthrough §3 passed.

Preferred `flags` entries (objects). A list of failed `code` strings is also accepted.

Walkthrough / Nest-aligned codes:

| Code | Typical fail |
|------|----------------|
| `cue_off_table` / `ball_off_table` | Off cloth 0–100 × 0–50 |
| `blocked_lane` | Parked ball in corridor |
| `path_disconnected` / `path_empty` | Continuity |
| `path_not_from_cue` / `path_misses_object` | Path vs balls |
| `jump_needs_airborne` / `jump_zigzag` / `jump_airborne_tent` / `jump_misses_blocker` / `jump_blocker_ambiguous` | Jump QA (missing hop / kink / tent / miss / untagged obstacle) |
| `ghost_underivable` / `ghost_on_apex` | Cut ghost (derive failed — not “pin missing”) |
| `pocket_missing` / `pocket_not_near` / `path_misses_pocket` / `pocket_unmakeable` / `primary_ob_ambiguous` | Pocket vs path end; `pocket_unmakeable` = one driven primary OB (not “single ball on the map”) |
| `bank_needs_rail` / `kick_needs_rail` | Cushion |
| `combo_needs_two_balls` / `combo_bad_transfer` / `combo_blocked` | Combo |
| `carom_no_redirect` | Carom |
| `curve_used_jump_dash` / `curve_zigzag` | Massé/curve mis-tagged airborne or tent/zigzag |

Merge-ready:

```json
{ "ok": true, "flags": [] }
```

---

## 4. Full envelope example (structure only)

```json
{
  "schema_version": "1.0",
  "map": { },
  "catalog": { },
  "validation": { "ok": true, "flags": [] }
}
```

Fill `map` / `catalog` from §1–§2. Jump hop example: `RACKUP_JUMP_PATH_SPEC.md` sotd-15 replacement `intended_path` (collinear over `(45, 25.2)`).

---

## 5. Ingest API (propose) — RackUp / roc

Not implemented on Nest yet. Contract for when roc wires it:

```http
POST {RACKUP_API}/v1/realai/sotd/propose
Content-Type: application/json
```

Body = `SotdProposeEnvelope`.

Alternate RealAI ability (same JSON in `result`):

```json
{
  "ability": "sotd_catalogue_propose",
  "payload": { }
}
```

Until that ships: roc merges files by hand from a validated envelope.

**roc owns** the renderer + `sotd-shot-maps.ts` / `SHOT_CATALOG` ingest PR on **Rack_em_up**.  
**This RealAI repo** ships docs only. Corrected **map patches** are a later Rack_em_up PR (`RACKUP_SOTD_CATALOGUE_AUDIT_PLAN.md`).
