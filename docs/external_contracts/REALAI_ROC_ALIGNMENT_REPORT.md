# RealAI ↔ ROC Alignment Report

**Date:** 2026-08-05  
**Plugin:** `rackup-coach` **v1.4.0**  
**Branch:** `unification/ultimate-all`  
**Source of truth:** `ROC_SYSTEM_DESIGN.md` (v1.1.0)  
**Status:** Ready for ROC host integration (provider-side)

---

## 1. What was added for ROC awareness

| Item | Location |
|------|----------|
| **`roc.py`** | Formats (`SINGLES` → `SCOTCH_DOUBLES` → `SCOTCH_JJ` → `TEAMS_5`), `format_config`, rating subjects by format, session context extractors, scotch/teams soft checks, format coaching notes, provider boundary (no ledger) |
| **Ability `roc_info`** | Discoverability: formats, game styles, format_config, boundary, finalize order |
| **Player fields** | `roc_league_id`, `season_id`, `session_id`, `format`, `game_style` on `PlayerProfile` |
| **Envelope notes** | Agent notes include rating chip + format when present |
| **METADATA / manifest** | v1.4.0 — `roc_league`, continuous rating, formats, display-band table |

RealAI still does **not** own: ledger, 45/35/20 split, session auto-payouts, projected payout UI, Nest persistence.

---

## 2. Rating + cross-league logic summary

### Continuous ladder (locked)

- **Single shared ladder:** `users.rating` (RackUp + ROC). No second competitive Elo.
- **Algorithm:** `elo_logistic_v1` (logistic expected score, K, game/Pyramid weights).
- **Owner of math:** RealAI `rating_update` → returns `rating_after`.
- **Owner of persistence:** RackUp only.
- **Default seed:** **500** → display **Advanced • 500** under locked bands (chip uses exact number always).

### Display bands (labels only — §7.1.2)

| Range | Label | Example chip |
|-------|-------|--------------|
| &lt;400 | Novice | Novice • 312 |
| 400–499 | Intermediate | Intermediate • 450 |
| 500–599 | Advanced | **Advanced • 547** |
| 600–699 | Expert | Expert • 640 |
| 700+ | Elite | Elite • 720 |

Matchmaking, handicaps, and `rating_update` use the **exact continuous number only**. Bands are echoed for UI.

Coach curriculum bands (beginner / intermediate / advanced / pro) remain separate for content selection on the same continuous scale.

### Cross-league conversion (§7.2)

| System | Conversion |
|--------|------------|
| **Fargo / BCA continuum (~200–800)** | Prefer pass-through (high confidence) |
| **APA SL** | Centers: 2→320, 3→420, 4→520, 5→600, 6→680, 7→760, 8+→820+ |
| **TAP** | Skill steps = APA centers; charter 20–100 → mid-pack stretch |
| **VNEA** | Tier / division → continuum centers |

**Preference order:** `primary_rating_system` → trusted recent → **Fargo/BCA → APA → TAP → VNEA**.  
After `matches_played_rackup ≥ 5`, shared ladder is competitive truth (externals stay badges only).

**Ability:** `rating_convert` returns `rackup_rating_estimate`, `band_label`, `display`, `confidence`, `equivalents`, `method: table_v1_roc`.

---

## 3. Abilities extended

All five game styles (`eight_ball`, `nine_ball`, `ten_ball`, `one_pocket`, `pyramid`) + ROC formats:

| Ability | ROC behavior |
|---------|----------------|
| **`league_validate`** | `game_style` + format + session ids; Pyramid matrix intact; scotch/teams soft warnings; `rating_subjects`; stop-if-invalid; next = `rating_update` |
| **`rating_update`** | Exact continuous before/after; format impact metadata; display chip echo; persist_hint for RackUp only |
| **`rating_convert`** | APA/BCA/Fargo/TAP/VNEA → continuum; seed_hint for one-time import |
| **`matchmaking`** | Convert missing ratings; rank on exact numbers; `rackup_equivalent_used` + confidence; format soft pref; never refuse mixed systems |
| **`coach` / `pyramid`** | Format coaching notes (scotch alternate-shot, teams boards); rating chip; Pyramid rules unchanged |
| **`shot_of_the_day`** | Primary game_style + continuous rating for copy; variety via `shown_shot_ids` |
| **`moderation`** | ROC channel / session ids; money-drama escalate on ROC chat |
| **`video_analysis`** | Game style + optional format tips |
| **`hall_context`** | ROC night + hall cloth/noise |
| **`pyramid_rules`** | Locked matrix preserved (7ft/10-ball, 9ft/15-ball, weights, call-shot) |
| **`roc_info`** | Host discovery |

### Format → rating subjects

| Format | Who gets `rating_update` |
|--------|---------------------------|
| Singles | Both individuals |
| Scotch Doubles / JJ | Both partners (`player_ids_json`) |
| Teams of 5 | Each board player played; team standings separate (RackUp) |

### Finalize order (confirmed)

```
1. Score + dual confirm
2. league_validate  → if valid === false: STOP
3. RackUp persist match + standings
4. rating_update per player in player_ids_json  → write rating_after
5. RackUp payout projections (money path independent)
6. Optional coach (non-blocking)
```

---

## 4. Updated call signatures

Documented in:

- `plugins/rackup_coach/examples/call_signatures.md` (section **ROC — Rack of Champions (v1.4)**)
- This report

**Transport:** `POST {REALAI_BASE_URL}/v1/plugins/rackup-coach`  
**Envelope:** `{ ability, player, payload, goal? }`

**New / notable payload fields:**

```
format: SINGLES | SCOTCH_DOUBLES | SCOTCH_JJ | TEAMS_5
game_style: eight_ball | nine_ball | ten_ball | one_pocket | pyramid
roc_league_id, season_id, session_id, match_id
player_ids_json, board_player_ids
opponent_rating (exact continuous)
league_ratings, primary_rating_system, matches_played_rackup
```

**New ability:** `roc_info` (alias `roc`)

**Response additions (typical):** `roc{}`, `band_label`, `rating_chip` / `display`, `format_coaching_notes`, `ladder: roc_continuous_shared`

---

## 5. Pyramid confirmation

Pyramid matrix **unchanged**:

| Skill | 7ft (10-ball) | 9ft (15-ball) | Call shot | Weight |
|-------|---------------|---------------|-----------|--------|
| Beginner | 25 | 40 | No | 0.7× |
| Intermediate | 35 | 55 | No | 0.85× |
| Advanced | 45 | 71 | Optional | 1.0× |
| Pro | 50 | 71 | Yes | 1.15× |

Classical scoring (1-ball = 11), designated cue only. ROC sessions may use Pyramid as `game_style` without rewriting rules.

---

## 6. Confirmation — ready for ROC host integration

| Check | Status |
|-------|--------|
| ROC formats + format_config understood by abilities | Yes |
| Continuous BCA-style ladder + display chips | Yes |
| Cross-league convert + mixed MM | Yes |
| Finalize path `league_validate` → persist → `rating_update` | Documented + ability fields |
| All major abilities format/game-style aware | Yes |
| Pyramid expanded, not broken | Yes |
| No ledger / UI ownership in RealAI | Yes |
| Call signatures + contract notes under `realai_documents/` | Yes |

**Host integration checklist**

1. Always pass continuous `player.rating` when known.  
2. On match finalize: `league_validate` first; only then persist; then `rating_update` per subject.  
3. Write only `rating_after` from RealAI — do not recompute Elo in Nest.  
4. Use `rating_convert` for APA/TAP/VNEA/Fargo import and mixed challenge MM.  
5. Pass `format` + `session_id` / `roc_league_id` on ROC calls for coaching + moderation context.  
6. Ledger 45/35/20 and auto-payouts remain entirely on RackUp.

---

## 7. Files touched (primary)

```
plugins/rackup_coach/roc.py                          (new)
plugins/rackup_coach/leagues.py                      (ROC scale + convert tables)
plugins/rackup_coach/types.py
plugins/rackup_coach/games.py
plugins/rackup_coach/coach_agent.py
plugins/rackup_coach/__init__.py
plugins/rackup_coach/manifest.yaml
plugins/rackup_coach/organs_bridge.py
plugins/rackup_coach/abilities/__init__.py
plugins/rackup_coach/abilities/league_validate.py
plugins/rackup_coach/abilities/rating_update.py
plugins/rackup_coach/abilities/rating_convert.py
plugins/rackup_coach/abilities/matchmaking.py
plugins/rackup_coach/abilities/coach.py
plugins/rackup_coach/abilities/moderation.py
plugins/rackup_coach/abilities/shot_of_the_day.py
plugins/rackup_coach/abilities/video_analysis.py
plugins/rackup_coach/abilities/hall_context.py
plugins/rackup_coach/examples/call_signatures.md
tests/test_roc_alignment.py                          (new)
C:\Users\tsmit\realai_documents\REALAI_ROC_ALIGNMENT_REPORT.md
```

---

*RealAI remains a clean intelligence provider. ROC money and persistence live in RackUp.*
