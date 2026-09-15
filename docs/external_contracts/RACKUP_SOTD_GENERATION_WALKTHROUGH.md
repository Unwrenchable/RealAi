# RealAI → RackUp SOTD generation walkthrough

**Date:** 2026-09-15  
**For:** roc / Rack_em_up (Nest ingest + renderer) + RealAI catalogue loop  
**Status:** Docs contract — RealAI emits validated JSON only; RackUp owns draw  
**Related:**

| Doc | Role |
|-----|------|
| `RACKUP_JUMP_PATH_SPEC.md` | Jump airborne dashed hop; never a solid massé-shaped kink |
| `RACKUP_GHOST_BALL_DIAGRAM_SPEC.md` | Cut contact geometry (`ghost_ball` / `contact_point`); offset **4.4** |
| `RACKUP_SOTD_NEW_ENTRY_SCHEMA.md` | Ingest envelope + `SotdShotMap` / `CatalogShot` fields |
| `RACKUP_SOTD_CATALOGUE_AUDIT_PLAN.md` | 52-map audit batches (A); this walkthrough is B+C |

**Out of scope here:** Ghost Ball tutorial copy, marketing site copy, SVG/canvas draw, Nest/SPA code. Geometry + coach tip fields only.

---

## 0. Ownership (non-negotiable)

| System | Owns | Does **not** own |
|--------|------|------------------|
| **RealAI** | Review existing maps, makeability QA, emit a **new or corrected** catalogue envelope (`map` + `catalog` + `validation`) | Drawing the table, `ShotMapDiagram`, merging TypeScript modules |
| **RackUp** | Live draw (`shot-map-geometry.ts`, `ShotMapDiagram.tsx`), ingest merge into `sotd-shot-maps.ts` / `SHOT_CATALOG` | Inventing jump/ghost geometry rules (those live in the specs above) |

```
existing map + shot-catalog tip
        │
        ▼
RealAI review + category rules + makeability QA
        │
        ▼
JSON envelope  (schema_version / map / catalog / validation)
        │
        ▼
RackUp Nest ingest  →  sotd-shot-maps.ts  +  SHOT_CATALOG
        │
        ▼
RackUp renderer draws  (roc owns this PR)
```

Live catalogue draw stays RackUp local maps. RealAI does **not** draw SOTD at request time.

**This loop is not** `ability.sotd_contribute` (provider-local grown library under `REALAI_DATA_DIR`). That ability stores coach-approved *practice* shots. Catalogue ingest is Nest `SOTD_SHOT_MAPS` + `SHOT_CATALOG`.

---

## 1. Load map + matching catalog tip

Checklist:

- [ ] Resolve id `sotd-NN` (zero-padded, `sotd-01` … `sotd-52` for the live set).
- [ ] Load **map** from RackUp `rackup-backend/src/realai/v2/sotd-shot-maps.ts` (`SOTD_SHOT_MAPS`, type `SotdShotMap`).
- [ ] Load **matching tip text** from `rackup-backend/src/shots/shot-catalog.ts` (`SHOT_CATALOG`, type `CatalogShot`) with the **same** `id`.
- [ ] Confirm `map.name` and `catalog.name` agree (or record a rename in the emit).
- [ ] Confirm `map.category` and `catalog.category` agree.
- [ ] Confirm `map.tip_zone` and `catalog.tipZone` agree (snake vs camel).
- [ ] Confirm `map.difficulty` and `catalog.difficulty` agree (`Easy` \| `Medium` \| `Hard` \| `Insane`).
- [ ] Read cloth coords: **x 0–100** head → foot, **y 0–50** near → far (9-foot aspect 2:1). Same plane as jump + ghost specs.
- [ ] Do **not** start from ASCII art alone. `ascii_table` is optional legend; geometry is `cue_ball_start` / `object_ball_positions` / `intended_path`.

If either side is missing, **fail** the load step — do not invent a catalog tip to match a map, or a map to match a tip.

---

## 2. Category rules

Apply the rule for `map.category`. Fail the review if the path contradicts the category (a jump drawn as massé, a combo that tunnels through a parked ball, etc.).

### Jump → airborne dashed

Contract: `RACKUP_JUMP_PATH_SPEC.md`.

- [ ] `category === "jump"` **never** uses a solid polyline that arcs around a blocker in table Y. That shape is reserved for `masse` / cloth swerve.
- [ ] Required segment kinds:

| Segment | `style` | `kind` |
|---------|---------|--------|
| CB → takeoff | `solid` | `ground` |
| takeoff → landing (via optional apex) | **`dashed`** | **`airborne`** |
| landing → OB contact | `solid` | `ground` |
| OB → pocket | `solid` | `object` |
| CB after contact | `dashed` | `cue_after` |

- [ ] Hop crosses **blocker.x** (takeoff.x < blocker.x < landing.x, or swapped if CB is foot-side).
- [ ] Ghost Ball, if any, is at **post-landing OB contact** — never on the airborne apex (`RACKUP_GHOST_BALL_DIAGRAM_SPEC.md`).
- [ ] Known jump ids (priority): `sotd-15`, `sotd-32`, `sotd-45`, `sotd-50`.

### Cut → Ghost Ball

Contract: `RACKUP_GHOST_BALL_DIAGRAM_SPEC.md`.

- [ ] Aim line: OB center → pocket (or next combo ball).
- [ ] Ghost CB center sits on that line **behind** the OB, center-to-center offset **4.4** map units.
- [ ] Live show rule: `showGhost = !isCombo && cut > 12 && cut < 78 && !railFirst`.
- [ ] Prefer map `ghost_ball` (+ optional `contact_point`) when present; else Nest/SPA derive.
- [ ] Do **not** emit ghost for rail-first shots.
- [ ] Combos: default hide; only force `ghost_ball.show: true` for first-OB → second-ball aim.
- [ ] No tutorial / marketing copy in the envelope.

### Combo → contact, no tunnel

- [ ] Path visits **at least two** object balls on the transfer line.
- [ ] No path through intervening balls **without a contact** (lane clearance; Nest `LANE_CLEARANCE = 2.4`).
- [ ] At each transfer, the driven ball leaves along the **line of centers** (Nest `COMBO_ALIGN_MAX_DEG = 14`).
- [ ] Do not skip past a combo ball.

### Carom → hit first OB, then redirect toward second

- [ ] CB path contacts the **first** object ball.
- [ ] After contact, CB **redirects** toward the second object (or designated helper) — not a straight line that only clips one ball.
- [ ] First-contact ball is not required to pocket; the carom is the CB continuation.
- [ ] Do not encode the carom as a jump dashed hop.

### Bank / kick → rail contact segments

- [ ] **Bank:** at least one plausible **cushion bounce on the object-ball path** (after OB contact).
- [ ] **Kick:** at least one plausible **cushion bounce before** the object ball (CB path).
- [ ] Bounce vertices sit on a rail (`near` / `far` / `head` / `foot`) and reflection is plausible (Nest `REFLECT_MAX_DEG = 32`).
- [ ] Path segments include the rail-hit points (do not draw a chord that skips the cushion).

### Massé / curve → never jump dashed for cloth swerve

- [ ] Cloth swerve / massé stays **on the cloth**: solid (or a non-airborne style). **Never** `kind: "airborne"` / jump dashed for a curve around a blocker.
- [ ] Jump dashed is reserved for a ball that **leaves the cloth** over a blocker (`RACKUP_JUMP_PATH_SPEC.md`).
- [ ] `sotd-50` (Venom-Style Jump-Curve Tease): if truly jump+curve, **airborne still dashed**; curve only **after landing**.

---

## 3. Makeability QA flags (pass/fail)

Run these after category rules. Envelope `validation.ok` is **true** only when every flag **passes**. Put failing codes in `validation.flags[]` (see schema doc). Align with Nest `validateSotdShotMap` in `sotd-shot-map-geometry.ts` where a code already exists.

### 3.1 Balls in cloth 0–100 × 0–50 with clearance

| Flag | Pass | Fail code (Nest-aligned) |
|------|------|--------------------------|
| Cue on cloth | `cue_ball_start` in playing surface with inset (`BALL_INSET = 2.0`) | `cue_off_table` / `cue_missing` |
| Object balls on cloth | every `object_ball_positions[]` in 0–100 × 0–50 with inset (~1.2) | `ball_off_table` |
| Lane clearance | parked balls (blockers/props) are **not** in the travel corridor (`LANE_CLEARANCE = 2.4`) unless they are a **contact** or the segment is **airborne** over a `role: "blocker"` | `blocked_lane` |
| At least one OB | `object_ball_positions.length >= 1` | `no_object_balls` |

Ball diameter in cloth units: **2.25** (2.25″ on 100″ 9-ft cloth).

### 3.2 `intended_path` continuity

| Flag | Pass | Fail code |
|------|------|-----------|
| Non-empty | ≥ 1 segment | `path_empty` |
| Connected | gap(`seg[i-1].to`, `seg[i].from`) ≤ **1.6** | `path_disconnected` |
| Starts at CB | gap(first.from, `cue_ball_start`) ≤ **3.5** | `path_not_from_cue` |
| Approaches primary OB | some path point within **6.5** of primary object | `path_misses_object` |
| Optional styles | `style`: `solid` \| `dashed` (default solid); `kind`: `ground` \| `airborne` \| `object` \| `cue_after` | record unknown values in flags |

### 3.3 Jump: no solid massé-shaped kink; airborne over blocker.x

| Flag | Pass | Fail code |
|------|------|-----------|
| Has airborne | some segment `kind === "airborne"` **or** `style === "dashed"` before OB contact, and that hop **crosses blocker.x** | `jump_needs_airborne` / `missing airborne` |
| No solid kink | no **solid/ground** vertex with bend > **28°** (`JUMP_ZIGZAG_MAX_DEG`) over the blocker (massé-shaped zigzag) | `jump_zigzag` |
| Jump spec QA-1 | `category==jump` && solid midpoint with `\|y − cue.y\| ≥ 4` while x between CB and OB → **fail** (massé-shaped jump) | `jump_zigzag` |

See `RACKUP_JUMP_PATH_SPEC.md` QA flags 1–2 and the sotd-15 replacement path.

### 3.4 Ghost Ball present or derivable for cuts 12–78°

| Flag | Pass | Fail |
|------|------|------|
| Cut window | cut angle in **(12°, 78°)** and **not** rail-first and **not** combo (unless `ghost_ball.show === true`) | n/a — ghost not required outside window |
| Present or derivable | map has `ghost_ball {x,y}` **or** OB + pocket (aim target) are present so SPA can derive at offset **4.4** | `ghost_underivable` |
| Placement | ghost is behind OB on the aim line, not on a jump apex | `ghost_on_apex` |

Cuts outside 12–78°, rail-first banks, and default combos: **pass** this flag without emitting ghost.

### 3.5 `pocket_target` consistent with object path end

| Flag | Pass | Fail code |
|------|------|-----------|
| Pocket exists | `pocket_target` set | `pocket_missing` |
| Near a pocket | within **8** of a table pocket (jump may target a cloth-edge pocket) | `pocket_not_near` |
| Path ends there | last segment `.to` within **8** of `pocket_target` | `path_misses_pocket` |

Pocket centers (same as Nest `POCKETS`):

| Id | (x, y) |
|----|--------|
| head-near | (0, 0) |
| head-far | (0, 50) |
| side-near | (50, 0) |
| side-far | (50, 50) |
| foot-near | (100, 0) |
| foot-far | (100, 50) |

### 3.6 Category extras (fail the review if skipped)

- [ ] Bank: `bank_needs_rail` if no post-contact cushion bounce.
- [ ] Kick: `kick_needs_rail` if no pre-contact cushion bounce.
- [ ] Combo: `combo_needs_two_balls` / `combo_bad_transfer` / `combo_blocked`.
- [ ] Carom: CB hits first OB then redirects toward second (no Nest code yet — emit `carom_no_redirect` if the CB path never turns toward the second ball).
- [ ] Curve/massé: `curve_used_jump_dash` if cloth swerve is tagged `airborne`.

**Do not emit** an ingest envelope with `validation.ok: true` when any of the above fail. RealAI may still emit `ok: false` with flags so roc can see the defects — that is a **review artifact**, not merge-ready.

---

## 4. Emit entry

Output **one JSON envelope** matching `RACKUP_SOTD_NEW_ENTRY_SCHEMA.md`. RealAI outputs validated JSON only — no PNG, no SVG, no tutorial HTML.

Checklist:

- [ ] `schema_version`: `"1.0"`
- [ ] `map`: full `SotdShotMap` (required fields + optional `ghost_ball` / `contact_point` / short `ascii_table`)
- [ ] `catalog`: full `CatalogShot` tip object (tagline, setup[], steps[], …) — **same `id`** as `map.id`
- [ ] `validation`: `{ "ok": true, "flags": [] }` for merge-ready; otherwise `ok: false` and populated flags
- [ ] `map.source`: `"realai"` for a **new** id; `"catalog_fallback"` for an audited/corrected existing `sotd-NN`
- [ ] Jump maps include `style` / `kind` on every hop segment
- [ ] Cut maps in the 12–78° window include `ghost_ball` (and `contact_point` when the touch point is not the obvious midpoint)
- [ ] Coach fields are **drill tips** (setup, stroke, mistakes) — not Ghost Ball teaching copy

Minimal shape:

```json
{
  "schema_version": "1.0",
  "map": { },
  "catalog": { },
  "validation": { "ok": true, "flags": [] }
}
```

`ascii_table` may be omitted or a short legend. Nest currently stores a string on live maps; ingest may fill a placeholder if absent.

---

## 5. RackUp ingest (roc)

**roc owns the renderer / ingest PR on Rack_em_up.** This RealAI PR is docs only.

Nest merge targets:

| Envelope | Nest module |
|----------|-------------|
| `map` | `rackup-backend/src/realai/v2/sotd-shot-maps.ts` → `SOTD_SHOT_MAPS` |
| `catalog` | `rackup-backend/src/shots/shot-catalog.ts` → `SHOT_CATALOG` |
| types mirror | `rackup-web/src/lib/types.ts` (`style` / `kind`, additive `ghost_ball`) |
| draw | `shot-map-geometry.ts` + `ShotMapDiagram.tsx` (already specified) |

Ingest rules for roc:

- [ ] Reject `validation.ok !== true` for merge.
- [ ] Upsert by `id` (`sotd-NN` or a new `sotd-NN` past 52).
- [ ] Map envelope `source: "catalog_fallback"` → Nest `SotdMapSource` **`"catalogue"`**.
- [ ] Map envelope `source: "realai"` → Nest **`"realai"`**.
- [ ] Keep `map.id === catalog.id`.
- [ ] First **corrected map patches** for the live 52 land on **Rack_em_up** in a **separate** PR — not this RealAI docs PR. See `RACKUP_SOTD_CATALOGUE_AUDIT_PLAN.md`.

Proposed ability later (not required to land these docs): `POST /v1/plugins/rackup-coach` with `ability: "sotd_catalogue_propose"` returning this envelope. Until Nest wires that, RealAI hands roc the JSON; roc pastes/merges.

---

## 6. Worked sketch (jump, not for merge)

`sotd-15` Jump Over the Troublemaker — **broken** live path is a solid kink through `(45, 32)`. Correct hop is in `RACKUP_JUMP_PATH_SPEC.md`. After QA, emit envelope with `map.id: "sotd-15"`, `source: "catalog_fallback"`, airborne dashed over blocker #7, ghost at post-landing OB contact if the cut window applies. **Do not merge that patch from this repo.**
