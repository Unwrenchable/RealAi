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
| `moderation` | Toxicity, harassment, money drama, sandbagging |
| `video_analysis` | Structured feedback from host checklist/notes |
| `matchmaking` | Candidate ranking by rating/style/form |
| `rating_intel` | Trajectory, volatility, next-band distance |
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
