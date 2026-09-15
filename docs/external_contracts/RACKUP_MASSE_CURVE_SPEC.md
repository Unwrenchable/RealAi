# Massé / cloth-swerve curve contract — RackUp SOTD maps

**Date:** 2026-09-15  
**For:** roc / Rack_em_up (Nest + SPA) + RealAI catalogue corrections  
**Related:**

| Doc | Role |
|-----|------|
| `RACKUP_JUMP_PATH_SPEC.md` | Jump airborne is a **straight** plan-view hop over the blocker — not a curve, not a tent |
| `RACKUP_GHOST_BALL_DIAGRAM_SPEC.md` | Contact geometry (derive / `showGhost`); not the swerve stroke |
| `RACKUP_SOTD_GENERATION_WALKTHROUGH.md` | Category + makeability QA |

**Scope:** Spec + path fields only. No massé tutorial, site marketing, or instructional UI copy.

When RealAI specifies or fixes **massé / curve / cloth swerve** diagrams, the cue path on the cloth must read as a **smooth curve**, never an angled polyline tent or zigzag.

---

## Rule

| Look | Allowed for |
|------|-------------|
| Smooth curve (dense arc samples **or** a renderer curve primitive) | `masse`, `curve`, cloth swerve after a landing |
| Straight dashed hop through the blocker `(x, y)` in plan view (overhead) | `jump` airborne only — `RACKUP_JUMP_PATH_SPEC.md` |
| Angled tent / apex / zigzag polyline | **Nothing** that should look like massé (or jump) |

A 2–3 vertex “V” or “N” through a blocker in table Y is **not** a massé. That shape is a catalogue bug (same class as the sotd-15 solid kink). Do **not** reserve zigzag for massé / swerve.

---

## Encoding

Prefer, in order:

1. Renderer-owned curve (`ShotMapDiagram` / geometry derive strokes a quadratic or cubic through control points), **or**
2. Dense samples along an arc — enough points that segments do not read as corners (typically ≥ 8–12 samples for a visible swerve).

Do **not** encode cloth swerve as:

- two segments meeting at an off-line apex (tent)
- a solid or dashed 90° kink
- `kind: "airborne"` (leaves-the-cloth is jump only)

`intended_path` may stay `{ from, to }[]` if samples are dense. Optional later: a `curve` / control-point field — roc owns draw.

---

## QA

1. `category === "masse"` or `"curve"` && path has a vertex bend ≳ **28°** with long legs (polyline tent / zigzag) → **fail** `curve_zigzag`.
2. Same categories && any `kind: "airborne"` / jump-dashed swerve → **fail** `curve_used_jump_dash` (existing).
3. Jump maps that use a tent (even dashed) fail under `RACKUP_JUMP_PATH_SPEC.md` (`jump_airborne_tent` / `jump_zigzag`), not this file.

---

## Out of scope for RealAI

No Rack_em_up code in this PR. roc wires a smooth curve draw if the SPA still strokes polylines as sharp corners.
