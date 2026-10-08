# RackUp Coach (`rackup-coach`)

First-class **living** RealAI plugin for the RackUp pool app.

| | |
|--|--|
| Plugin id | `rackup-coach` |
| Package | `plugins.rackup_coach` |
| Organ | `organ.rackup-coach` |
| Manifest | `manifest.yaml` |

## Abilities

| Ability | Description |
|---------|-------------|
| `coach` | Rating-aware pro coaching (beginner → pro) |
| `shot_of_the_day` | Practical daily shot (not trick-shot spam) |
| `shot_of_the_day` + `payload.mode: "sotd_validate"` | Deterministic SOTD map checker + diagram-prompt renderer (see below) |
| `moderation` | Toxicity, harassment, money drama, sandbagging |
| `video_analysis` | Structured feedback from host checklist/notes |
| `matchmaking` | Candidate ranking by rating/style/form |
| `rating_intel` | Trajectory, volatility, next-band distance |
| `player_card_sync` | Unified Player Card (ROC Glicko + Fargo + shadow RackUpRate) |
| `tournament` | Event prep + league notes |
| `hall_context` | Hall cloth/noise/session adaptations |

Uses organs: Frontal/Prefrontal, Amygdala, Cerebellum, Hippocampus, memory stack, Creativity Furnace, Guardian, Intuition, Limbic, etc. (see `manifest.yaml`).

## Example

```python
from plugins.rackup_coach import invoke
invoke({"ability": "shot_of_the_day", "player": {"player_id": "p1", "rating": 620,
        "weaknesses": ["cue_ball_control"]}})
```

See `examples/call_signatures.md` for full RackUp integration shapes.

## SOTD map checker (`mode: "sotd_validate"`)

`sotd_checker.py` is pure Python geometry with no LLM. The map is the source of truth. The checker fills
`cut_deg`, `blocked_by` and `tangent_side` before it writes the sentence or the
diagram prompt. Travis's standing instruction is saved verbatim in
`prompts/sotd_checker.txt` and is only for a future LLM step.

- **Axis:** `x_long`. x runs 0..100 (head to foot) and y runs 0..50 (left to right, measured from the head end).
  Pockets: `corner_head_left (0,0)`, `corner_head_right (0,50)`,
  `side_left (50,0)`, `side_right (50,50)`, `corner_foot_left (100,0)`,
  `corner_foot_right (100,50)`.
- **Checks:** place, called, ghost, path (cue to ghost, and object to pocket), cut
  (over 70 is a pro-only warning, over 80 fails), tangent, claim (regex only).
- **Fixes, in order:** nudge the cue to the open side, drop the blocking ball, swap to the open
  pocket with the smaller cut, or use a catalog map (`SOTD_MAP_CATALOG`). A claim that disagrees with the
  validated geometry is replaced by the rendered sentence (`claim_rerender`).
- **Image:** generated only when `ok` is true and `render_diagram` is set. The default is no backend
  (`diagram: null` plus `diagram_error`). Opt in with
  `REALAI_SOTD_IMAGE_BACKEND=xai` and `XAI_API_KEY` in the hive env. A failed image
  never fails a passed map.
- **HTTP style:** a failed map returns envelope `ok: true` (the plugin ran) with
  `result.ok: false`. It never crashes.

```python
invoke({
    "ability": "shot_of_the_day",
    "goal": "validate sotd map, then render copy and diagram",
    "player": {"discipline": "nine_ball"},
    "payload": {
        "mode": "sotd_validate",
        "render_diagram": True,
        "map": {
            "id": "sotd-2026-10-08", "game": "nine_ball",
            "cue": {"x": 28, "y": 18},
            "balls": [{"n": 1, "x": 62, "y": 14}, {"n": 2, "x": 78, "y": 36}],
            "called": {"ball": 1, "pocket": "corner_foot_right"},
            "stroke": {"tip": "center", "speed": "medium"},
            "claim": "Cut the 1 in the foot-right corner and stop for the 2.",
        },
    },
})
# -> result.cut_deg 53.2, tangent_side "left", claim fails (stop on a 53 deg cut;
#    the 2 is not on the exit side), sentence re-rendered:
#    "Cut the 1 in the foot-right corner with center ball at medium speed and come off the tangent."
```
