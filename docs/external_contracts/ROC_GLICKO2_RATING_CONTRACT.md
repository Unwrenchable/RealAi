# ROC Glicko-2 Player Ladder Contract

**Document version:** 1.0.0  
**Date:** 2026-08-05  
**Status:** LOCKED — official ROC singles player ladder  
**Plugin:** `rackup-coach` **v1.5.0**  
**Module:** `plugins/rackup_coach/glicko2.py`  
**Related:** `ROC_SYSTEM_DESIGN.md`, `REALAI_ROC_ALIGNMENT_REPORT.md`, `REALAI_RACKUP_WIRING_CONTRACT.md`

---

## 0. Locked decisions

| Decision | Value |
|----------|--------|
| Player ladder | **Glicko-2** continuous rating |
| Display format | `"{band} • {rating}"` e.g. **Advanced • 547** |
| Teams/doubles TrueSkill | **Not in this pass** |
| Cross-league | Convert → **seed + high RD** → Glicko-2 takes over |
| Math owner | **RealAI** (`rating_update`) |
| Persistence owner | **RackUp** (`rating`, `rd`, `volatility`) |
| Ledger / money | **Not RealAI** |

### Display bands (labels only)

| Rating | Band |
|--------|------|
| &lt;400 | Novice |
| 400–499 | Intermediate |
| 500–599 | Advanced |
| 600–699 | Expert |
| ≥700 | Elite |

Bands **never** drive matchmaking windows, handicaps, or Glicko inputs.

### Defaults

| Parameter | Value |
|-----------|--------|
| Default rating | **500** |
| Default RD | **175** |
| Default volatility (σ) | **0.06** |
| Min RD | **30** |
| Max RD | **350** |
| τ (tau) | **0.5** |

---

## 1. Core API (`glicko2.py`)

```python
from plugins.rackup_coach.glicko2 import (
    PlayerRating,
    band_for,
    update_glicko2,
    apply_match,
    apply_match_for_player,
    seed_from_external,
)

# Player state
PlayerRating(rating=500, rd=175, volatility=0.06, player_id="u1")

# Labels
band_for(547)  # → "Advanced"

# One-sided update
update_glicko2(player, opp_rating=560, opp_rd=90, score=1.0)

# Dual update (pre-match states for both)
apply_match(winner, loser)  # → winner_after, loser_after, deltas

# Cross-league seed
seed_from_external(520, confidence=0.68, from_system="apa")
```

---

## 2. Finalize path (unchanged order)

```
1. Score report + dual confirm
2. league_validate          → if valid === false: STOP
3. RackUp persists match
4. rating_update (Glicko-2) → write rating, rd, volatility for each subject
5. RackUp payout projections (independent)
6. Optional coach (non-blocking)
```

**Never** recompute Glicko in Nest for production ROC matches.

---

## 3. `rating_update` envelope

### Request

```json
{
  "ability": "rating_update",
  "player": {
    "player_id": "u1",
    "rating": 547,
    "rd": 80,
    "volatility": 0.06,
    "discipline": "nine_ball",
    "matches_played_rackup": 12
  },
  "payload": {
    "opponent_id": "u2",
    "opponent_rating": 560,
    "opponent_rd": 90,
    "opponent_volatility": 0.06,
    "won": true,
    "format": "SINGLES",
    "game_style": "nine_ball",
    "roc_league_id": "roc_vegas",
    "session_id": "ses_week3",
    "match_id": "m_99",
    "player_ids_json": ["u1", "u2"]
  }
}
```

Aliases: `opp_rating`, `opp_rd`, `vol` / `sigma`, `my_score`+`opp_score` instead of `won`.

### Response (shape)

```json
{
  "ok": true,
  "ability": "rating_update",
  "result": {
    "algorithm": "glicko2_v1",
    "ladder": "roc_glicko2",
    "player_id": "u1",
    "winner_after": {
      "player_id": "u1",
      "rating": 561.2,
      "rd": 77.4,
      "volatility": 0.0598,
      "band": "Advanced",
      "display": "Advanced • 561"
    },
    "loser_after": {
      "player_id": "u2",
      "rating": 547.1,
      "rd": 87.2,
      "volatility": 0.0601,
      "band": "Advanced",
      "display": "Advanced • 547"
    },
    "deltas": {
      "winner_rating": 14.2,
      "loser_rating": -12.9,
      "winner_rd": -2.6,
      "loser_rd": -2.8
    },
    "rating_before": 547,
    "rating_after": 561.2,
    "rd_before": 80,
    "rd_after": 77.4,
    "display_before": "Advanced • 547",
    "display_after": "Advanced • 561",
    "persist_hint": {
      "fields_to_write": ["rating", "rd", "volatility", "rating_updated_at", "last_match_delta"],
      "write_value": { "rating": 561.2, "rd": 77.4, "volatility": 0.0598 },
      "owner": "RackUp DB — RealAI does not persist ratings",
      "never_recompute_in_nestjs": true
    }
  }
}
```

*(Exact after-values depend on inputs; shape is stable.)*

---

## 4. Cross-league convert + seed flow

```
APA / BCA / Fargo / TAP / VNEA
        │
        ▼
 rating_convert  (table estimate + confidence)
        │
        ▼
 seed_from_external(estimate, confidence)
        │  → rating continuous
        │  → RD elevated when confidence low
        │  → volatility = 0.06
        ▼
 RackUp one-time seed of users.rating / rd / volatility
        │  (only if matches_played_rackup == 0)
        ▼
 Subsequent matches → rating_update (Glicko-2 only)
```

### Example convert request

```json
{
  "ability": "rating_convert",
  "player": {
    "player_id": "p_new",
    "matches_played_rackup": 0,
    "league_ratings": { "apa": 4 },
    "primary_rating_system": "apa"
  },
  "payload": {
    "from_system": "apa",
    "from_value": 4,
    "from_scale": "skill_1_9"
  }
}
```

### Example convert result (essentials)

```json
{
  "rackup_rating_estimate": 520,
  "band_label": "Advanced",
  "display": "Advanced • 520",
  "confidence": 0.68,
  "ladder": "roc_glicko2",
  "glicko2_seed": {
    "rating": 520,
    "rd": 150,
    "volatility": 0.06,
    "band": "Advanced",
    "display": "Advanced • 520",
    "method": "seed_from_external_glicko2"
  },
  "seed_hint": {
    "when": "matches_played_rackup == 0 and no ROC Glicko history",
    "write_once": { "rating": 520, "rd": 150, "volatility": 0.06 },
    "do_not_reseed_over_history": true
  }
}
```

---

## 5. Matchmaking & rating_intel

| Ability | Glicko usage |
|---------|----------------|
| `matchmaking` | Exact continuous rating; **RD widens pair windows**; expected score; convert foreign → seed RD |
| `rating_intel` | Current rating + RD + σ; provisional when RD high; next **display** band distance |
| `league_validate` | Unchanged score rules; then host calls `rating_update` |
| Coach / Pyramid / SOTD | Unbroken; Pyramid matrix still coaching/skill metadata |

---

## 6. Storage fields (RackUp)

| Field | Type | Notes |
|-------|------|--------|
| `users.rating` | number | Continuous Glicko rating (integer display OK) |
| `users.rd` | number | Rating deviation |
| `users.volatility` | number | σ |
| `users.rating_updated_at` | timestamptz | Optional |
| External APA/BCA/… | profile | Display + convert seed only |

---

## 7. Out of scope (this pass)

- Teams of 5 / Scotch **TrueSkill** team ladder  
- Ledger, splits, payouts  
- Nest recomputation of ratings  

---

## 8. Confirmation

**RealAI rackup-coach v1.5.0 is ready for ROC host integration on the singles Glicko-2 ladder.**

1. Pass `rating`, `rd`, `volatility` on every rated call when known.  
2. Finalize: `league_validate` → persist → `rating_update`.  
3. Persist `rating` + `rd` + `volatility` from `winner_after` / `loser_after` (or `player_after`).  
4. Seed new players once via `rating_convert` → `glicko2_seed`.  
5. Display chips: `band_label` + rating, e.g. Advanced • 547.  
6. Do not re-seed after ROC match history exists.

---

*File: `C:\Users\tsmit\realai_documents\ROC_GLICKO2_RATING_CONTRACT.md`*
