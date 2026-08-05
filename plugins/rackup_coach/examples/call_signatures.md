# RackUp ↔ RealAI `rackup-coach` call signatures

All calls are **provider-level**: pass player context and payloads from RackUp.
No NestJS or database code lives in this plugin.

## Python (direct)

```python
from plugins.rackup_coach import invoke, register, COACH

# --- Shot of the Day ---
invoke({
    "ability": "shot_of_the_day",
    "player": {
        "player_id": "usr_123",
        "display_name": "Alex",
        "rating": 640,
        "discipline": "nine_ball",
        "weaknesses": ["cue_ball_control", "position_play"],
        "strengths": ["long_potting"],
        "recent_results": [
            {"opponent_rating": 610, "won": False},
            {"opponent_rating": 655, "won": True},
        ],
        "table_speed": "medium",
    },
    "payload": {"count": 2, "hint": "draw"},
})

# --- Moderation ---
invoke({
    "ability": "moderation",
    "player": {"player_id": "usr_456", "rating": 720},
    "payload": {
        "text": "You're sandbagging at a 400 rating you hustler",
        "context": {"prior_flags": 1, "channel": "match_chat"},
    },
})

# --- Full coach (basic→pro by rating) ---
invoke({
    "ability": "coach",
    "goal": "I freeze up in money matches",
    "player": {
        "player_id": "usr_123",
        "rating": 880,
        "discipline": "eight_ball",
        "weaknesses": ["match_pressure", "safety_play"],
    },
    "payload": {"mode": "full", "minutes": 60},
})

# --- Video analysis (host sends checklist / notes, not raw decode) ---
invoke({
    "ability": "video_analysis",
    "player": {"player_id": "usr_123", "rating": 510},
    "payload": {
        "video_meta": {"clip_type": "stroke", "duration_s": 12},
        "checklist": {"stance_stable": False, "follow_through": False, "grip_tension": False},
        "observations": "jabbing at the ball, head lifts",
    },
})

# --- Matchmaking support ---
invoke({
    "ability": "matchmaking",
    "player": {"player_id": "usr_123", "rating": 700},
    "payload": {
        "candidates": [
            {"player_id": "a", "rating": 690, "style": "safety"},
            {"player_id": "b", "rating": 820, "style": "aggressive"},
        ],
        "window": 70,
    },
})

# --- Rating intelligence ---
invoke({
    "ability": "rating_intel",
    "player": {"player_id": "usr_123", "rating": 705,
               "recent_results": [{"won": True, "opponent_rating": 690}]},
    "payload": {
        "rating_history": [{"rating": 660}, {"rating": 680}, {"rating": 705}],
    },
})

# --- Tournament ---
invoke({
    "ability": "tournament",
    "player": {"player_id": "usr_123", "rating": 750},
    "payload": {
        "event": {"name": "Friday 9-Ball", "format": "single_elim", "race_to": 5},
        "upcoming_opponent": {"rating": 770, "style": "break_and_run"},
    },
})

# --- Hall / session context ---
invoke({
    "ability": "hall_context",
    "player": {"player_id": "usr_123", "rating": 600, "hall_name": "Main St Billiards"},
    "payload": {
        "hall": {"id": "hall_1", "cloth": "fast", "noise_level": "high"},
        "session": {"games_played": 7},
    },
})
```

## Register on RealAI model

```python
from plugins.rackup_coach import register
register(model)  # exposes model.rackup_coach / rackup_shot_of_the_day / rackup_moderate
model.rackup_shot_of_the_day({"player": {"player_id": "p1", "rating": 500}})
```

## Organs hive

```python
from modules.organs import call_organ

call_organ(
    "organ.rackup-coach",
    goal="shot of the day for intermediate nine-ball player",
    payload={
        "ability": "shot_of_the_day",
        "player": {"player_id": "p1", "rating": 620, "weaknesses": ["break"]},
    },
)
```

## HTTP (once server loads plugin routes or host proxies)

Suggested host→RealAI shapes (JSON body):

| RackUp feature | `ability` | Key payload fields |
|----------------|-----------|--------------------|
| Shot of the Day card | `shot_of_the_day` | `player`, optional `count`, `hint` |
| Chat filter | `moderation` | `player`, `payload.text`, `payload.context` |
| Coach tab | `coach` | `player`, `payload.mode`, `goal` |
| Video review | `video_analysis` | `checklist`, `video_meta`, `observations` |
| Find match | `matchmaking` | `candidates[]` |
| Rating panel | `rating_intel` | `rating_history`, results |
| Event prep | `tournament` | `event`, `upcoming_opponent` |
| Check-in | `hall_context` | `hall`, `session` |

Response envelope:

```json
{
  "ok": true,
  "plugin": "rackup-coach",
  "ability": "shot_of_the_day",
  "result": { "...ability specific..." },
  "organ_trace": [{ "organ_id": "organ.cerebellum", "ok": true, "notes": "..." }],
  "notes": "band=intermediate rating=640",
  "error": null
}
```

## RackUp Pyramid

```python
from plugins.rackup_coach import invoke

# Rules matrix + race state
invoke({
  "ability": "pyramid_rules",
  "player": {"player_id": "p1", "rating": 720, "table_size": "7ft", "skill_level": "advanced"},
  "payload": {"my_score": 20, "opp_score": 18},
})

# Shot of the Day for 7ft beginner Pyramid
invoke({
  "ability": "shot_of_the_day",
  "player": {
    "player_id": "p1", "rating": 350, "discipline": "pyramid",
    "table_size": "7ft", "skill_level": "beginner",
    "weaknesses": ["cue_ball_control", "pattern_play"],
  },
  "payload": {"game": "pyramid"},
})

# Full Pyramid coach on 9ft pro (first to 71, call-shot yes)
invoke({
  "ability": "pyramid",
  "player": {
    "player_id": "p1", "rating": 950, "discipline": "pyramid",
    "table_size": "9ft", "skill_level": "pro",
  },
  "payload": {"mode": "pyramid", "my_score": 40, "opp_score": 38},
})
```

| Skill | 7ft (10-ball) | 9ft (15-ball) | Call shot | Weight |
|-------|---------------|---------------|-----------|--------|
| Beginner | 25 | 40 | No | 0.7× |
| Intermediate | 35 | 55 | No | 0.85× |
| Advanced | 45 | 71 | Optional | 1.0× |
| Pro | 50 | 71 | Yes | 1.15× |

## Multi-game + cross-league (v1.3)

```python
from plugins.rackup_coach import invoke

# 8-ball coach
invoke({"ability": "coach", "player": {"player_id": "p", "rating": 1100, "discipline": "eight_ball"}})

# 9-ball SOTD
invoke({"ability": "shot_of_the_day", "player": {"player_id": "p", "rating": 1000, "discipline": "nine_ball", "weaknesses": ["position_play"]}})

# Convert APA SL 5 → RackUp
invoke({"ability": "rating_convert", "player": {"player_id": "p"}, "payload": {"from_system": "apa", "from_value": 5, "from_scale": "skill_1_9"}})

# Mixed-league matchmaking
invoke({
  "ability": "matchmaking",
  "player": {"player_id": "p", "rating": 1200, "discipline": "eight_ball", "league_ratings": {"apa": 4}, "primary_rating_system": "apa", "matches_played_rackup": 2},
  "payload": {"candidates": [
    {"player_id": "x", "league_ratings": {"apa": 3}, "primary_rating_system": "apa"},
    {"player_id": "y", "rating": 1180}
  ]}
})

# Game knowledge pack
invoke({"ability": "game_knowledge", "player": {"player_id": "p", "discipline": "one_pocket"}})
```

Disciplines: eight_ball | nine_ball | ten_ball | one_pocket | pyramid  
League systems: apa | bca | tap | vnea (convert to shared RackUp ladder)
