# Multi-Game + Cross-League Expansion Report

**Date:** 2026-08-05  
**Branch:** unification/ultimate-all  
**Plugin:** rackup-coach **v1.3.0**  
**Source of truth:** `C:\Users\tsmit\realai_documents\RACKUP_GAME_KNOWLEDGE_AND_AI_CONTRACT.md`

## Game knowledge added
| Discipline | Module | Content |
|------------|--------|---------|
| eight_ball | `games.py` | Objective, rack, rules, fouls, good/bad, band coaching, weight 1.0 |
| nine_ball | `games.py` | Lowest-first, push-out, race formats, weight 1.0 |
| ten_ball | `games.py` | Call-shot rotation, weight 1.05 |
| one_pocket | `games.py` | Pocket race, defense-first, weight 1.1 |
| pyramid | `games.py` + existing `pyramid.py` | Locked matrix preserved |

Aliases normalized from RackUp product strings (`8-ball` → `eight_ball`, etc.).

## Cross-league conversion / matchmaking
| Feature | Module |
|---------|--------|
| APA/BCA/TAP/VNEA → RackUp | `leagues.py` `to_rackup` / tables |
| Equivalents snapshot | `equivalents_from_rackup` |
| Preference order (primary → trusted → APA→BCA→TAP→VNEA → shared) | `resolve_effective_rating` |
| Ability `rating_convert` | `abilities/rating_convert.py` |
| Mixed-league candidate ranking | `matchmaking.py` `_candidate_rating` |

## Abilities extended
- `coach` — multi-game knowledge pack + discipline coaching
- `shot_of_the_day` — game-specific shots (8/9/10/one-pocket/pyramid)
- `video_analysis` — discipline-aware findings
- `rating_update` — game weights (1.0/1.0/1.05/1.1 + Pyramid matrix)
- `league_validate` — race games + Pyramid
- `matchmaking` — cross-league + shared ladder
- **New:** `rating_convert`, `game_knowledge`

## Call signatures (new/updated)
```
POST /v1/plugins/rackup-coach
ability: rating_convert | game_knowledge | coach | shot_of_the_day | matchmaking | ...
player.discipline: eight_ball|nine_ball|ten_ball|one_pocket|pyramid
player.league_ratings: { apa, bca, tap, vnea }
player.primary_rating_system, matches_played_rackup
```

See `plugins/rackup_coach/examples/call_signatures.md`.

## Confirmation
**RealAI rackup-coach now supports the full multi-game + cross-league RackUp surface** per the knowledge contract, without breaking Pyramid (locked matrix intact).
