# rackup-coach

**Plugin id:** `rackup-coach`  
**Importable package:** `plugins.rackup_coach`  
(Python package directories use underscores; the plugin *name* remains `rackup-coach`.)

See `../rackup_coach/` for implementation, `manifest.yaml`, and abilities.

## Quick start

```python
from plugins.rackup_coach import invoke

invoke({
  "ability": "shot_of_the_day",
  "player": {"player_id": "p1", "rating": 620, "weaknesses": ["cue_ball_control"]},
})
```

Full call signatures: `../rackup_coach/examples/call_signatures.md`
