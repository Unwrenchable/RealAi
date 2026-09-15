# RackUp SOTD catalogue audit plan (52 maps)

**Date:** 2026-09-15  
**For:** roc / Rack_em_up map-patch PR + RealAI reviewers  
**Status:** Audit plan only — **no map JSON in this RealAI PR**  
**Related:** `RACKUP_SOTD_GENERATION_WALKTHROUGH.md`, `RACKUP_SOTD_NEW_ENTRY_SCHEMA.md`, `RACKUP_JUMP_PATH_SPEC.md`, `RACKUP_GHOST_BALL_DIAGRAM_SPEC.md`

This is deliverable **A** (plan). Walkthrough + schema are **B + C**. First **corrected map patches** land on **Rack_em_up** via a **separate PR**. Do not merge geometry into this RealAI docs PR.

Live sources (Rack_em_up `main`):

- Maps: `rackup-backend/src/realai/v2/sotd-shot-maps.ts` (`SOTD_SHOT_MAPS`, 52)
- Tips: `rackup-backend/src/shots/shot-catalog.ts` (`SHOT_CATALOG`)
- Validator: `rackup-backend/src/realai/v2/sotd-shot-map-geometry.ts` (`validateSotdShotMap`)

---

## 0. Live category census (52)

Counts from `SOTD_SHOT_MAPS` (must stay 52 until ingest adds ids):

| Category | Count | Batch |
|----------|------:|-------|
| position | 16 | 6 |
| bank | 8 | 4 |
| kick | 7 | 4 |
| combo | 5 | 3 |
| novelty | 5 | 6 |
| curve | 4 | 5 |
| jump | 4 | **1** |
| carom | 2 | 2 |
| masse | 1 | 5 |
| **total** | **52** | |

---

## 1. Batch order

| Batch | Category | IDs | Why first |
|-------|----------|-----|-----------|
| **1** | jump (4) | sotd-15, 32, 45, 50 | Known solid massé-shaped hop; airborne + ghost where applicable |
| **2** | carom (2) | sotd-09, 25 | CB must hit first OB then redirect |
| **3** | combo (5) | sotd-08, 18, 31, 40, 42 | No tunnel through intervening balls |
| **4** | bank (8) + kick (7) | banks sotd-01, 13, 19, 21, 27, 34, 46, 51; kicks sotd-07, 17, 22, 28, 36, 39, 44 | Rail contact segments |
| **5** | curve (4) + masse (1) | curve sotd-05, 14, 30, 37; masse sotd-16 | Never jump-dashed cloth swerve |
| **6** | position (16) + novelty (5) | remaining ids below | Cuts → Ghost Ball; leftover QA |

Do not skip batch 1. Jump is the documented production bug (`RACKUP_JUMP_PATH_SPEC.md`).

---

## 2. Per-map checklist (every id)

Copy this onto each `sotd-NN`. Pass/fail. Emit a `SotdProposeEnvelope` (`catalog_fallback`) only when the walkthrough QA is green — **into the Rack_em_up patch PR**, not here.

### Identity

- [ ] Map id `sotd-NN` matches `SHOT_CATALOG` id
- [ ] `name` / `category` / `difficulty` / `tip_zone` ↔ `tipZone` agree

### Cloth + path (walkthrough §3)

- [ ] Balls in cloth **0–100 × 0–50** with clearance (`cue_off_table`, `ball_off_table`, `blocked_lane`)
- [ ] `intended_path` continuity (connected, starts at CB, approaches OB)
- [ ] `pocket_target` near a pocket and consistent with object path end

### Jump contract (`RACKUP_JUMP_PATH_SPEC.md`) — all maps; **blocking** if `category === "jump"`

- [ ] No solid massé-shaped kink over a blocker (`jump_zigzag`)
- [ ] Has dashed `kind: "airborne"` (or dashed before contact) **crossing blocker.x** (`jump_needs_airborne`)
- [ ] Ground segments stay straight; hop is takeoff → apex → landing
- [ ] Ghost, if any, is post-landing OB contact — **not** the apex

### Ghost Ball contract (`RACKUP_GHOST_BALL_DIAGRAM_SPEC.md`) — cuts

- [ ] Cut 12–78°, not rail-first, not combo (unless forced): `ghost_ball` present **or** derivable at offset **4.4**
- [ ] `contact_point` optional; midpoint of ghost CB and OB if omitted
- [ ] No ghost on rail-first; combo default hide
- [ ] No tutorial / marketing copy added to `CatalogShot`

### Category extras (walkthrough §2)

- [ ] **Jump** — airborne dashed (batch 1)
- [ ] **Carom** — CB hits first OB then redirects toward second
- [ ] **Combo** — contact each transfer ball; no path through intervening balls without contact
- [ ] **Bank** — rail contact on **object** path
- [ ] **Kick** — rail contact on **cue** path before OB
- [ ] **Curve / massé** — never `kind: "airborne"` for cloth swerve
- [ ] **Position / novelty** — still run cloth + path + ghost-if-cut

### Emit / ingest

- [ ] Envelope `schema_version: "1.0"`
- [ ] `validation.ok === true` before roc merges
- [ ] `source: "catalog_fallback"` → Nest `"catalogue"`
- [ ] Patch PR target: **Unwrenchable/Rack_em_up** (`sotd-shot-maps.ts` + `SHOT_CATALOG` if tip text changes)

---

## 3. Batch 1 — jumps (priority)

Known clone bug: solid apex `(45, 32)` on an otherwise straight CB→OB line. Reads as massé. Fix template in `RACKUP_JUMP_PATH_SPEC.md`.

| id | name | difficulty | Cue (live) | Blocker | OB | Same bug |
|----|------|------------|------------|---------|-----|----------|
| **sotd-15** | Jump Over the Troublemaker | Hard | (24, 25.5) | #7 (45, 25.2) | #1 (70, 25.2) | YES — **fix first** |
| **sotd-32** | Jump-Draw Hybrid Tease | Insane | (23, 25) | #7 (46.2, 25) | #1 (71.2, 25) | YES — same pattern |
| **sotd-45** | Elevator Jump Over the Rack Ghost | Insane | (24, 25.5) | #7 (45, 25.6) | #1 (70, 25.6) | YES |
| **sotd-50** | Venom-Style Jump-Curve Tease | Insane | (26, 25) | #7 (45, 25.4) | #1 (70, 25.4) | YES — airborne still dashed; curve **after landing** only |

Sibling template (scale to each `blocker.x`):

- takeoff.x = blocker.x − 6  
- apex = (blocker.x, cue.y + 5) as **dashed airborne**  
- landing.x = blocker.x + 6  
- ground y ≈ cue / ball line  

After hop: add `ghost_ball` when the post-landing OB cut is in 12–78° and not rail-first.

**sotd-15 replacement `intended_path`:** copy from `RACKUP_JUMP_PATH_SPEC.md` (do not re-invent).

---

## 4. Remaining ids by batch

### Batch 2 — carom (2)

| id | name | difficulty |
|----|------|------------|
| sotd-09 | Carom Off the 9 | Medium |
| sotd-25 | Double Kiss Escape | Hard |

Checklist add: CB path vertex at first OB; next CB segment aims at second ball (not a jump dash).

### Batch 3 — combo (5)

| id | name | difficulty |
|----|------|------------|
| sotd-08 | Simple Combo: Spot to Corner | Easy |
| sotd-18 | Frozen Combo Rail Run | Hard |
| sotd-31 | Three-Ball Line Combo | Medium |
| sotd-40 | Celebration Combo Off Two | Hard |
| sotd-42 | Machine-Gun Line | Hard |

Checklist add: ≥2 object balls on the transfer line; `combo_blocked` / `combo_bad_transfer`. Ghost default **off**.

### Batch 4 — bank (8) + kick (7)

**Banks**

| id | name | difficulty |
|----|------|------------|
| sotd-01 | Rail-First Bank Cross | Medium |
| sotd-13 | Bank the 9 Off Two Rails | Insane |
| sotd-19 | Wing Shot Bank | Hard |
| sotd-21 | Reverse English Bank | Insane |
| sotd-27 | Lengthwise Bank Cross-Corner | Hard |
| sotd-34 | Dead Ball Bank (Soft) | Medium |
| sotd-46 | Snake Along the Rail | Hard |
| sotd-51 | Massey Mirror Banks | Hard |

**Kicks**

| id | name | difficulty |
|----|------|------------|
| sotd-07 | Two-Rail Kick to Corner | Hard |
| sotd-17 | Rail-First Kick Safety | Medium |
| sotd-22 | Ticket Pocket Thin Kick | Hard |
| sotd-28 | Soft Safety: Hide Behind the 8 | Medium |
| sotd-36 | Jump-Kick Hybrid Plan | Hard |
| sotd-39 | Quad Rail Dream (Path Only) | Insane |
| sotd-44 | Around-the-World CB Tour | Hard |

Checklist add: rail vertices + plausible reflection. **No ghost** on rail-first. `sotd-36` is **kick**, not jump — do not borrow jump dashed unless there is a real airborne hop (if there is, tag it `airborne` and still keep the kick rail-before-OB).

### Batch 5 — curve (4) + masse (1)

| id | name | difficulty | category |
|----|------|------------|----------|
| sotd-05 | Inside English Cut | Hard | curve |
| sotd-14 | Curve Around a Blocker | Hard | curve |
| sotd-30 | Clockwise Curve Drag | Medium | curve |
| sotd-37 | Spin-to-Win Rail First | Hard | curve |
| sotd-16 | Massé Orbit (Training Version) | Insane | masse |

Checklist add: cloth swerve is **not** `kind: "airborne"`. `sotd-05` is a cut with inside english — Ghost Ball still applies if 12–78° and not rail-first. `sotd-37` is rail-first → no ghost.

### Batch 6 — position (16) + novelty (5)

**Position**

| id | name | difficulty |
|----|------|------------|
| sotd-02 | Stop-Shot Ladder | Easy |
| sotd-03 | Draw Back Two Diamonds | Medium |
| sotd-04 | Follow Into the Stack | Easy |
| sotd-06 | Outside English Hold | Hard |
| sotd-10 | Rail Cut Thin as Hair | Hard |
| sotd-11 | Force Follow Over Distance | Medium |
| sotd-12 | Power Draw Escape | Hard |
| sotd-20 | Length of the Table Stop | Hard |
| sotd-23 | Stack Split with Soft Stun | Medium |
| sotd-26 | Side-Pocket Soft Cut | Medium |
| sotd-29 | Elevated Draw Over a Rail Nip | Hard |
| sotd-33 | Hold-Up English Along the Rail | Hard |
| sotd-35 | Point-to-Point Long Pot | Easy |
| sotd-38 | The Spotlight 8 Cut | Medium |
| sotd-48 | Swing-Cut Showboat | Hard |
| sotd-49 | Impossible-Looking Thin Cut | Insane |

**Novelty**

| id | name | difficulty |
|----|------|------------|
| sotd-24 | Behind-the-Back Novelty (Rail Assist) | Medium |
| sotd-41 | Butterfly Spread | Hard |
| sotd-43 | Squeeze Between Friends | Insane |
| sotd-47 | Coin Prop Freeze (Optional Prop) | Hard |
| sotd-52 | Rapid-Fire Spot Shots | Medium |

Checklist add: thin cuts (`sotd-10`, `sotd-26`, `sotd-38`, `sotd-48`, `sotd-49`, …) get Ghost Ball when in 12–78°. Straight stop/draw/follow: ghost usually **off** (cut too thick). Props (`sotd-47`) must stay on cloth with clearance.

---

## 5. Tracking (for the Rack_em_up patch PR)

Suggested columns: `id`, `batch`, `category`, `jump_ok`, `ghost_ok`, `path_ok`, `envelope_ok`, `merged`.

Batch 1 (4 maps) is the first merge candidate. roc may ship sotd-15 alone, then siblings, then later batches.

```
RealAI docs PR (this repo)     →  walkthrough + schema + this plan
Rack_em_up map-patch PR (roc)  →  intended_path / ghost_ball / SHOT_CATALOG text
Rack_em_up renderer PR (roc)   →  draw dashed airborne + optional ghost override
```

Three PRs, three repos/surfaces. Do not combine map JSON into this RealAI PR.
