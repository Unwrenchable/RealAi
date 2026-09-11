# RackUp Game Knowledge + AI Integration Contract

**Document version:** 1.0.0  
**Date:** 2026-08-05  
**Status:** **SOURCE OF TRUTH** — RealAI implements against this document  
**Audience:** RealAI maintainers (`rackup-coach` plugin) + RackUp NestJS engineers  
**Related:** `REALAI_RACKUP_WIRING_CONTRACT.md` (transport/envelope detail; this doc supersedes for **game knowledge**, **cross-league ratings**, and **ability semantics**)  
**Plugin:** `rackup-coach` **1.2.0+**  
**Canonical endpoint:** `POST {REALAI_BASE_URL}/v1/plugins/rackup-coach`

---

## 0. Authority & system boundary

| System | Owns | Does **not** own |
|--------|------|------------------|
| **RealAI** | Game intelligence, coaching content, moderation decisions, **rating calculation**, matchup scoring, Pyramid rules math, SOTD generation/variety, cross-league conversion estimates, video feedback structure | UI, Nest routes as product surface, Postgres, WebSockets fanout, auth sessions, friend graph storage, media blob storage |
| **RackUp** | Product shell: auth, halls, friends, match lifecycle, chat delivery, storing **results** RealAI returns (ratings, flags, shown SOTD ids), candidate pre-filter for matchmaking | Inventing skill math, reimplementing Pyramid scoring, coaching content, moderation ML |

**One sentence:** RackUp is the product shell; RealAI is the **intelligence provider**. Every skill change, matchup ranking, league score check, moderation decision, coaching plan, video critique, Shot of the Day, Pyramid rule config, and cross-league rating estimate is computed by RealAI; RackUp displays and persists.

```
RackUp (Nest + DB + WS + UI)
   │  HTTPS JSON  POST /v1/plugins/rackup-coach
   ▼
RealAI rackup-coach (abilities + organs)
   │  result envelopes
   ▼
RackUp persists / renders (never recompute skill math)
```

### Discipline / game style codes (stable strings)

| Code | Display | Notes |
|------|---------|-------|
| `eight_ball` | 8-Ball | Also accept aliases: `8-ball`, `8ball` |
| `nine_ball` | 9-Ball | `9-ball`, `9ball` |
| `ten_ball` | 10-Ball | `10-ball`, `10ball` |
| `one_pocket` | One Pocket | `one-pocket`, `onepocket` |
| `pyramid` | RackUp Pyramid | `rackup-pyramid`, `rackup_pyramid` |

RackUp stores match `game` as product strings (`8-ball`, `9-ball`, `10-ball`, `one-pocket`, `rackup-pyramid`). RealAI **normalizes** to the codes above.

### Shared RackUp rating (single ladder)

- **Field:** `users.rating` (integer), default seed **500**, clamp **100–3000**.
- **One number for all games.** Game/style does **not** create separate ladders.
- **Weighting** after a match changes *how much* the number moves (`rating_weight`, K, discipline), not which ladder is used.
- RealAI may also report **league-equivalent views** (APA/BCA/TAP/VNEA estimates) without replacing the shared number.

---

# A. All game styles (full knowledge RealAI needs)

For every discipline, RealAI coaching, SOTD, video analysis, and matchmaking notes must be **discipline-aware**.

## A.1 8-Ball (APA / BCA style)

### Objective
Pocket all of **your group** (solids 1–7 **or** stripes 9–15), then legally pocket the **8-ball** in a **called** pocket (call-shot for the 8 is universal in APA/BCA-style bar/league play; some house rules call every shot).

### Rack
- **15 object balls** + cue.
- Traditional triangle: **8 in the center**, one solid and one stripe at the back corners; remaining balls alternate randomly.
- Break from behind the head string (kitchen).

### Key rules (intelligence defaults)
1. Open table after break until a player legally pockets a ball of one group without foul → that group is theirs.
2. Combination shots: object ball of **your** group must be first contacted (after groups are assigned), except special 8-ball combo rules in some codes—prefer: you may not use opponent’s ball as first contact to pocket your own.
3. **8-ball early** (pocketed before clearing group) = loss (common APA/BCA house).
4. Scratch or foul while shooting the 8 = **loss** if 8 is pocketed on the foul; if 8 stays up, opponent usually gets ball-in-hand (ruleset-dependent: APA often ball-in-hand behind the line or full BIH—RealAI should note “ruleset: APA vs BCA” when known).
5. Scratch on break: typically opponent BIH behind head string or full BIH per league code.
6. Balls pocketed on break: usually count if open-table rules allow; groups may remain open.

**Default assumption when `ruleset` omitted:** hybrid **BCA-friendly** call-shot on 8; full **ball-in-hand** after fouls (common bar-table digital scoring). When `league_code` is `APA`, prefer APA-specific wording (handicaps, 8 on break win/loss house variants).

### Common fouls
| Foul | Typical result |
|------|----------------|
| Scratch / cue ball pocketed | Ball-in-hand (or kitchen) for opponent |
| Wrong ball first | BIH / loss of turn |
| No rail after contact (when required) | Foul |
| Jump illegal / push shot | Foul |
| 8 early / 8 wrong pocket | Loss |
| Touching balls / double hit | Foul |

### Good play vs bad play

| Good | Bad |
|------|-----|
| Clear easy balls while leaving shape | Chase low-percentage combos early |
| Keep 8 path open; plan last 2–3 balls | Block own 8 with own ball |
| Safety when table is dry | Fire at thin cut with no out |
| Control cue ball after break | Wild power break with no plan |
| Know when to play safe vs run out | Always offense at SL-3 pace |

### Skill-level coaching emphasis

| Band (shared rating ~) | Coaching focus |
|------------------------|----------------|
| Novice (&lt;900) | Ghost-ball aim, stop shot, simple patterns, don’t leave 8 blocked |
| Intermediate (900–1499) | 2–3 ball patterns, center-ball position, soft vs firm speed |
| Advanced (1500–2099) | Two-way shots, safety exchanges, 8-ball endgame |
| Pro (2100+) | Maximum outs, table management, psychological pace |

### Rating weight (default for `rating_update`)
- Standard 8-ball match: **`rating_weight` = 1.0** unless handicap or short race says otherwise.
- Money / high-stakes: host may pass `k_factor` higher; RealAI applies, does not invent stakes policy.

---

## A.2 9-Ball

### Objective
Legally pocket the **9-ball** (typically after contact with the lowest-numbered ball on the table first). Race formats common (race to 5, 7, 9, etc.).

### Rack
- Balls **1–9** diamond rack; **1 on the foot spot**, **9 in the center**, others random.
- Break from kitchen; often must drive 4 balls to rails or equivalent local rule.

### Key rules
1. Always contact **lowest numbered ball** first (push-out after break optional in many codes).
2. Any legally pocketed ball stays down; **9 on break** may win (local/tournament rules—flag `nine_on_break_wins`).
3. Combination / carom onto 9 is legal if lowest ball is first contact.
4. Scratch → usually **ball-in-hand** anywhere (pro rules) or behind line (bar rules)—use `ball_in_hand_mode`: `table` | `kitchen`.
5. 9 pocketed illegally → spot 9, lose turn (or loss depending on code).

### Common fouls
Scratch; wrong ball first; no rail; jump foul; three-foul rule in some tournaments (loss of game).

### Good vs bad play

| Good | Bad |
|------|-----|
| Pattern from high balls back to 9 | Kill shape leaving thin cuts on 1/2 |
| Two-way safety when stuck | Always blast 9 early without shape |
| Soft roll for shape after break | Break-and-run force with no out |
| Know push-out strategy | Ignore opponent’s runout threat |

### Skill-level coaching
| Band | Focus |
|------|-------|
| Novice | Lowest-first discipline, stop/follow basics |
| Intermediate | 3-ball sequences, natural shape |
| Advanced | Banks, kicks, safety wars, break strategy |
| Pro | Pattern efficiency, multi-rail position, match pace |

### Rating weight default
**1.0**. Short races (race to 3) may pass slightly higher volatility via `k_factor` if RackUp chooses.

---

## A.3 10-Ball

### Objective
Call-shot rotation: pocket balls 1–10 in order context; win by legally pocketing the **called 10**. Stricter than 9-ball (usually **call every shot**, including combinations).

### Rack
- Balls **1–10** triangle; **1 on foot spot**, **10 in center**.
- Often **alternate break**, winner breaks, or loser breaks—pass `break_policy` when known.

### Key rules
1. Call ball **and** pocket (standard WPA-style 10-ball).
2. Lowest ball first contact.
3. Early 10 illegally → spot and loss of turn (not always loss of game).
4. Early 10 legally only if called correctly after sequence rules.
5. Push-out after break often allowed (one shot).

### Common fouls
Same family as 9-ball, plus **wrong pocket / uncalled** for called shots.

### Good vs bad play

| Good | Bad |
|------|-----|
| Precise call-shot discipline | “Slop” mindset from bar 9-ball |
| Safety when no out | Force thin 10 |
| Controlled break for a ball | Wild break scattering with no shot |

### Skill-level coaching
Emphasize **call accuracy**, **cue ball for next lowest**, and **safety under pressure**. Higher bands: multi-rail position and intentional safeties.

### Rating weight default
**1.05** suggested (slightly more skill-sensitive than bar 9-ball) unless host overrides. RealAI should accept host `rating_weight` as authority.

---

## A.4 One Pocket

### Objective
Score **points** by pocketing balls into **your** designated corner pocket only. Race is typically **first to 8** (classic) or another agreed number (`race_to`).

### Rack
- 15 object balls. Breaker chooses pocket (or lag winner chooses).
- Deep strategic game; defense-first often correct.

### Key rules (defaults)
1. Only your pocket scores for you.
2. Balls in opponent’s pocket usually score for them.
3. Scratch / foul: typically **ball-in-hand** behind line or kitchen + possible **point penalty** (spot a ball or −1)—pass `foul_penalty`: `spot` | `point` | `bih_only`.
4. Intentionally pocketing in wrong pocket can gift opponent.
5. Frozen ball / rail rules matter; coaching must mention patience.

### Common fouls
Scratch; no rail; double hit; illegal jump; moving balls; pocketing cue.

### Good vs bad play

| Good | Bad |
|------|-----|
| Defense, clusters near your pocket | Open table for opponent’s run |
| Soft bank / freeze tactics | Over-aggression early |
| Count remaining + race math | Ignore scoreboard |
| Safety-first when behind | Panic offense |

### Skill-level coaching
| Band | Focus |
|------|-------|
| Novice | Which pocket is yours; simple banks; don’t scratch |
| Intermediate | Freezes, clusters, when to dig |
| Advanced | Multi-ball traps, score management |
| Pro | Psychological warfare, deep safety, endgame precision |

### Rating weight default
**1.1** (high skill ceiling / variance). Accept host override.

---

## A.5 RackUp Pyramid (locked rules — authoritative)

**Product name:** RackUp Pyramid  
**Discipline code:** `pyramid`  
**Scoring style:** Classical numbered-ball **points race**

### Objective
Be first to reach the **points-to-win** target for the match’s **table size × skill level**. Points come from pocketed object balls.

### Table → rack (locked)

| Table size | Rack (object balls) |
|------------|---------------------|
| **7 ft** | **10** balls (1–10) |
| **9 ft** | **15** balls (1–15) |

### Classical scoring (locked)
| Ball | Points |
|------|--------|
| **1** | **11** (not 1) |
| **2–15** | Face value (2 … 15) |
| Cue ball | **Never scores** (designated cue only) |

Re-rack / continue until a player hits the race target (live engine may track remaining balls and re-spot per product rules; intelligence treats scoreboard as point totals).

### Locked skill × table matrix (FINAL — do not drift)

| Skill level | 7 ft points (10-ball) | 9 ft points (15-ball) | Call shot | Rating weight |
|-------------|----------------------|----------------------|-----------|---------------|
| **Beginner** | **25** | **40** | No | **0.7×** |
| **Intermediate** | **35** | **55** | No | **0.85×** |
| **Advanced** | **45** | **71** | Optional | **1.0×** |
| **Pro** | **50** | **71** | Yes | **1.15×** |

String codes: `beginner` | `intermediate` | `advanced` | `pro`  
(Aliases from RackUp: `BEGINNER`, `INTERMEDIATE`, `ADVANCED`, `PRO`.)

### Call-shot semantics
| Mode | Meaning |
|------|---------|
| `no` | Pocketed legal object ball scores without calling pocket |
| `optional` | Call recommended; soft enforcement in coaching, validation may warn |
| `yes` | Must call ball+pocket (or ball+rail plan) before shot; miss-call → no score / loss of turn per product |

### Win condition
- **First to `points_to_win`** for the configured skill×table.
- Invalid for league commit: neither player ≥ target (unless `forfeit`); both ≥ target without clear winner.
- Margin for rating: `|my_score - opp_score|` when both provided.

### Good vs bad play (Pyramid-specific)

| Good | Bad |
|------|-----|
| Hunt **high value** (1-ball = 11, then high numbers) | Ignore 1-ball premium |
| Count remaining points on table | Play “like 8-ball groups” |
| Shape for next high-value | Kill CB after low ball |
| Endgame: know points needed | Chase impossible combos when short |

### Skill-level coaching (Pyramid)
| Skill | Coaching |
|-------|----------|
| Beginner | Value of 1-ball; simple pots; count to 25/40 |
| Intermediate | Routes of 2–3 balls; avoid scratches near target |
| Advanced | Optional call discipline; table-wide value maps |
| Pro | Mandatory call precision; rating weight 1.15—mistakes costly |

### Validation rules RealAI must enforce (`league_validate` / score checks)
1. `table_size` ∈ {`7ft`,`9ft`} → rack 10 or 15.
2. `skill_level` maps to matrix target.
3. Pocketed ball numbers ⊆ {1…rack_size}.
4. Classical point sum consistency when `pocketed_balls[]` provided (optional cross-check).
5. 1-ball contributes **11**.
6. Winner inference: first to target; forfeit flag bypasses score race.

### Full rack point totals (reference)
- 10-ball rack sum = 11+2+…+10 = **65**
- 15-ball rack sum = 11+2+…+15 = **130**  
(Useful for “points left on table” coaching.)

---

# B. Player-level intelligence RealAI owns

## B.1 Shared RackUp rating

| Property | Value |
|----------|-------|
| Name | RackUp rating |
| Storage owner | RackUp DB `users.rating` |
| Calculator | **RealAI only** via `rating_update` |
| Scale | Integer **100–3000** (soft continuum; new users often ~500) |
| Cross-game | **Single ladder** for all disciplines |
| Algorithm label | Prefer `elo_logistic_v1` (or document successor in `result.algorithm`) |

### How ratings move
1. After a match is **validated** and **persisted**, RackUp calls `rating_update` **once per participant** (winner perspective and loser perspective separately).
2. Inputs: pre-match ratings, outcome (won / scores), `game`/`discipline`, optional `table_size`, `skill_level`, `k_factor`, **`rating_weight`**, margin, forfeit.
3. RealAI returns `rating_after`, deltas, bands, optional Pyramid skill signals.
4. RackUp **writes** `rating_after` only—**never** re-Elo in Nest for production.

### Game-specific weighting (defaults if host omits `rating_weight`)

| Discipline | Default `rating_weight` |
|------------|-------------------------|
| eight_ball | 1.0 |
| nine_ball | 1.0 |
| ten_ball | 1.05 |
| one_pocket | 1.1 |
| pyramid | **From locked matrix** (0.7 / 0.85 / 1.0 / 1.15) |

`weighted_delta ≈ raw_delta × rating_weight` (exact formula owned by RealAI; expose in `result.input`).

### Failure policy
- Transport/5xx: RackUp retries once. Production should **not** write a local Elo unless `REALAI_FALLBACK_LOCAL_ELO` is explicitly enabled for dev.
- `ok: false`: no rating write; surface error.

## B.2 Suggested matchups / matchmaking signals

**Ability:** `matchmaking`

RackUp **pre-filters** candidates (online, region, friends, stakes, not blocked). RealAI **ranks** only.

Signals RealAI should use:
- Rating delta / window (default window ~70 RackUp points, expandable)
- Same `table_size` / `skill_level` preference (esp. Pyramid)
- Style tags (`aggressive`, `safety`, …) when provided
- Recent form from `player.recent_results`
- Cross-league fairness when candidates only have APA/BCA/TAP/VNEA (see §C)
- Soft prefer friends / same hall when `payload.preferences` set

Output: `ranked_candidates[]` with `fit_score`, `in_window`, notes; `best`; `policy`.

## B.3 League scorekeeping + submission validation

**Ability:** `league_validate`

Before RackUp commits league/Pyramid (or strict rated) scores:
1. Call `league_validate` with scores, game, table/skill, optional pocket log.
2. If `valid === false` → reject with `errors[]`.
3. If `valid === true` → persist match → `rating_update` each side.

Applies to Pyramid always; for 8/9/10/one-pocket validate race bounds, non-negative scores, not both winners, forfeit flags.

## B.4 Chat moderation

**Ability:** `moderation`

**When:** Every chat message (or sampled + all reports) **before** broadcast/persist.

Categories to detect (non-exhaustive):
- Toxicity / insults / slurs  
- Harassment / threats  
- Sexual content toward users  
- Money-match drama / payment shaming  
- **Sandbagging** accusations & rating integrity bait  
- Doxxing / personal data  
- Spam / scam links  

**Actions RackUp switches on:**

| `action` | RackUp behavior |
|----------|-----------------|
| `allow` | Deliver |
| `soft_filter` | Deliver + soft nudge / rate-limit |
| `warn` | Deliver or hold per product policy + warn |
| `warn_and_flag` | Warn + T&S flag record |
| `hold_for_review` | **Do not deliver** |
| `block_and_escalate` | Drop + escalate |

Offline RealAI: RackUp may soft-allow with `policy_tags: ["offline_fallback"]` and queue delayed review—product choice.

## B.5 Professional coaching + practice plans

**Abilities:** `coach`, `pyramid`

Modes in `payload.mode`:
`full` | `practice_plan` | `pre_match` | `mental` | `pattern` | `pyramid`

Must be discipline-aware (§A). Pyramid mode includes race phase, value of 1-ball, points needed.

## B.6 Video analysis

**Ability:** `video_analysis`

RealAI does **not** require raw video bytes. RackUp stores media; send:
- `video_meta` (clip_type, duration, url_ref, fps)
- `checklist` (stance, follow-through, grip, elbow, …)
- `observations` free text  
Return findings, drills, scorecard, Pyramid expectation when relevant.

## B.7 Shot of the Day

**Ability:** `shot_of_the_day` (alias `sotd`)

Requirements:
1. Prefer transferable **match** skills, not pure trick shots (`not_a_trick_shot: true` preferred).
2. Always include **`why_this_shot`** and **`why_helps_regular_play`** (RackUp UI must surface).
3. Variety: respect `payload.shown_shot_ids[]` (last ~14–30).
4. Personalize via weaknesses, discipline, table size, skill, recent results.
5. Pyramid variants when `discipline=pyramid`.

## B.8 Hall / session context

**Ability:** `hall_context` (and fields on every `player` object)

Use when present:
- `hall_id`, `hall_name`, `table_speed`, cloth/noise notes in payload  
- Check-in social context (friends at hall) only as **soft** coaching/matchmaking flavor—not privacy violation  

Adapt practice plans (faster cloth → more stun control) and SOTD setup language.

---

# C. Cross-league rating & matchmaking intelligence

RealAI must convert and reason across **BCA**, **APA**, **TAP**, and **VNEA** so players who only have one league number can still be matched fairly on the **shared RackUp ladder**.

## C.1 What each system means

### BCA (Billiard Congress of America / related skill numbers)
- Often used as a **skill continuum number** or points-style rating depending on local BCA league software.
- In RackUp import pipelines, raw BCA-like values may be small integers; Nest’s historical unifier used rough `×10` toward RackUp scale—**RealAI owns improved conversion**.
- **Low:** recreational / new league player  
- **Mid:** solid house player  
- **High:** strong amateur / semi-pro  

Treat `league_ratings.bca` as **higher-is-stronger** unless `bca_scale` says otherwise.

### APA (American Poolplayers Association)
- **Skill levels (SL)** typically **2–7** (sometimes 1–9) for 8-ball/9-ball formats.
- Handicap system is **not** pure Elo; SL is a band, not a fine-grained continuum.
- **SL 2–3:** beginner/intermediate bar  
- **SL 4–5:** strong intermediate  
- **SL 6–7:** advanced / near-pro amateur  

### TAP (The American Poolplayers / TAP pool leagues)
- Skill ratings commonly expressed on a **points / skill ladder** (often roughly comparable ordering to other amateur ladders; exact local scales vary).
- RealAI should treat TAP as **higher-is-stronger** continuous-ish score unless `tap_scale` provided.
- Map into same skill bands as APA/BCA via §C.3 tables; refine with data later.

### VNEA (Valley National 8-Ball Association)
- Coin-op / bar-box culture; skill levels / divisions vary by charter.
- Often **division or skill tier** rather than fine Elo.
- Higher designation ⇒ stronger; convert via band tables.

## C.2 RackUp shared scale (target continuum)

| RackUp rating | Skill band | Rough meaning |
|---------------|------------|---------------|
| 100–500 | novice / new | New app user, limited history |
| 500–900 | novice | Learning fundamentals |
| 900–1500 | intermediate | Consistent league filler |
| 1500–2100 | advanced | Strong amateur |
| 2100–3000 | pro / elite | High-level amateur / pro |

Default new user seed: **500**.

## C.3 Approximate conversion tables (v1 — refine with data)

These are **estimates for matchmaking & display**, not legal handicaps for APA/BCA scoring software.

### APA skill level → RackUp (center of band)

| APA SL | ≈ RackUp | Band |
|--------|----------|------|
| 2 | 700 | novice |
| 3 | 950 | intermediate |
| 4 | 1200 | intermediate |
| 5 | 1500 | advanced |
| 6 | 1850 | advanced |
| 7 | 2200 | pro |
| 8+ | 2500+ | pro |

Formula (smooth): `rackup ≈ clamp(400 + SL × 250, 100, 3000)` for SL ∈ [1,9].

### BCA-style number → RackUp

Two input modes:

1. **`bca_skill` 1–9 band** (if host labels it): use same centers as APA SL.  
2. **`bca_rating` continuous** (e.g. 40–90 or 400–900 depending on source):  
   - If value ≤ 100: `rackup ≈ clamp(value × 22, 100, 3000)` (v1 heuristic)  
   - If value &gt; 100: treat as already continuum-like: `rackup ≈ clamp(value, 100, 3000)` or `value × 2` if known Fargo-adjacent—prefer host `bca_scale`: `skill_1_9` | `raw_x10` | `continuum`.

Documented Nest legacy: `bca/scp → external × 10` then clamp—RealAI may supersede with better `scale` metadata.

### TAP → RackUp (v1 heuristic)

Assume TAP skill points roughly **0–20** or **20–100** depending on charter. Host should pass `tap_scale`.

| If TAP looks like… | Convert |
|--------------------|---------|
| 1–9 skill steps | Same as APA SL table |
| 20–100 “rating” | `rackup ≈ clamp(300 + tap × 20, 100, 3000)` |
| 200–800 Fargo-like | pass-through clamp |

### VNEA → RackUp (v1 heuristic)

| VNEA tier / SL | ≈ RackUp |
|----------------|----------|
| Division D / SL low | 800 |
| Division C | 1100 |
| Division B | 1500 |
| Division A | 1900 |
| Open / top | 2300+ |

If numeric 1–7: use APA-like formula.

### Worked example (contract requirement)

| Known | Estimate others (illustrative) |
|-------|--------------------------------|
| **BCA continuum ~450** (if scale = continuum mid-amateur) | RackUp ~450–900 depending on scale flag; if Nest-style `×10` → **4500 clamped to 3000** is wrong—prefer `bca_scale` |
| **BCA skill 4** (1–9) | RackUp **~1200**; APA **~4**; TAP skill **~4**; VNEA **~B** |
| **APA 5** | RackUp **~1500**; BCA skill **~5**; TAP **~ mid-high**; VNEA **~B/A** |
| **APA 3** | RackUp **~950** |

**Example preferred narrative for coach/UI:**  
“450 BCA (skill band) ≈ APA SL 3–4 ≈ RackUp ~1000–1200 ≈ TAP mid-pack ≈ VNEA C/B.”

RealAI must return structured equivalents, not only prose.

## C.4 Conversion ability & multi-rating preference

### Preference order when multiple league ratings exist
1. **`primary_rating_system`** if host sets it.  
2. Else **most recently verified** (`league_ratings[].updated_at` / `trusted: true`).  
3. Else priority: **APA** (if SL present) → **BCA** → **TAP** → **VNEA** → others.  
4. Always keep **RackUp shared rating** as competitive truth for `rating_update` once the player has match history on RackUp (`matches_played >= N`, suggest N=5). Until then, seed from best conversion.

### Ability: `rating_convert` (required)

Request payload:
```json
{
  "from_system": "apa",
  "from_value": 5,
  "from_scale": "skill_1_9",
  "also_known": [
    { "system": "bca", "value": 62, "scale": "raw", "updated_at": "2026-07-01" }
  ]
}
```

Response `result`:
```json
{
  "rackup_rating_estimate": 1500,
  "band": "advanced",
  "confidence": 0.72,
  "equivalents": {
    "apa": { "value": 5, "display": "SL 5" },
    "bca": { "value": 5, "display": "skill ~5", "alt_continuum": 68 },
    "tap": { "value": 5, "display": "skill ~5" },
    "vnea": { "value": "B", "display": "Division B" }
  },
  "method": "table_v1",
  "notes": "Estimate only; not official handicap."
}
```

### Matchmaking with mixed leagues
In `matchmaking` payload, candidates may include:
```json
{
  "player_id": "u2",
  "rating": null,
  "league_ratings": {
    "apa": 4,
    "bca": null,
    "tap": null,
    "vnea": null
  },
  "primary_rating_system": "apa"
}
```
RealAI converts each candidate to **internal RackUp-equivalent** for fit scoring, and returns both `fit_score` and `rating_delta` on the shared scale. Never refuse to rank solely because systems differ.

## C.5 What updates vs what is display-only

| Number | Updated by `rating_update`? | Role |
|--------|----------------------------|------|
| RackUp `rating` | **Yes** | Competitive truth |
| APA / BCA / TAP / VNEA | **No** (external leagues) | Import, display, convert, soft matchmaking |
| `equivalents` snapshot | Optional cache in RackUp | UI badges |

---

# D. Integration contract

## D.1 Transport

| Item | Value |
|------|-------|
| Base URL | `REALAI_BASE_URL` (default `http://127.0.0.1:8000`) |
| Canonical path | `POST /v1/plugins/rackup-coach` |
| Alias | `POST /v1/rackup/coach` |
| Content-Type | `application/json` |
| Headers | `X-Request-Id`, optional `Authorization`, `X-Provider: realai`, `X-RackUp-Tenant` |
| Auth model | Service-to-service; **no** end-user JWT required by RealAI |

## D.2 Universal request envelope

```json
{
  "ability": "string",
  "goal": "optional free-text intent",
  "organs_enabled": true,
  "player": {
    "player_id": "uuid",
    "display_name": "Alex",
    "rating": 640,
    "rating_system": "rackup",
    "discipline": "pyramid",
    "preferred_hand": "right",
    "weaknesses": ["cue_ball_control"],
    "strengths": ["long_potting"],
    "recent_results": [],
    "session_stats": {},
    "history_notes": [],
    "hall_id": "hall_123",
    "hall_name": "Main St Billiards",
    "table_speed": "medium",
    "locale": "en",
    "table_size": "7ft",
    "skill_level": "intermediate",
    "pyramid_skill": "intermediate",
    "pyramid_score": 0,
    "pyramid_opp_score": 0,
    "league_ratings": {
      "apa": 4,
      "bca": null,
      "tap": null,
      "vnea": null
    },
    "league_ratings_meta": {
      "apa": { "updated_at": "2026-06-01", "trusted": true, "scale": "skill_1_9" },
      "bca": { "scale": "continuum" }
    },
    "primary_rating_system": "apa",
    "matches_played_rackup": 12
  },
  "payload": {}
}
```

### Context RackUp will pass (by domain)

| Context | Fields | Used by |
|---------|--------|---------|
| Identity | `player_id`, `display_name` | All |
| Shared skill | `rating`, `rating_system=rackup`, `skill_level` | Rating, MM, coach, SOTD |
| League foreign keys | `league_ratings.{apa,bca,tap,vnea}`, meta, `primary_rating_system` | Convert, MM, coach copy |
| Game mode | `discipline`, `table_size` | Pyramid, SOTD, coach, validate |
| History | `recent_results[]`, weaknesses, strengths, notes | Coach, SOTD, MM, rating intel |
| Live match | scores, pocket logs | Validate, pyramid_rules, coach race |
| Hall | hall_id/name, table_speed | hall_context, SOTD |
| Social | optional friend flags, check-in soft prefs | MM only (RackUp filters hard constraints) |
| Chat | text + channel context | moderation |
| Media | video_meta, checklist, observations | video_analysis |
| Variety | `shown_shot_ids[]` | SOTD |
| Candidates | `candidates[]` | matchmaking |

**Rule:** RealAI never queries RackUp’s DB. History and league ratings must be **in the request**.

## D.3 Universal response envelope

```json
{
  "ok": true,
  "plugin": "rackup-coach",
  "ability": "rating_update",
  "result": {},
  "organ_trace": [],
  "notes": "",
  "error": null
}
```

HTTP 200 + `ok:false` = logical failure. 5xx/network = transport failure.

## D.4 Exact abilities RackUp will call

| Ability string | Aliases | Purpose |
|----------------|---------|---------|
| `rating_update` | `skill_update`, `post_match_rating` | Post-match shared rating |
| `rating_convert` | `convert_rating`, `league_convert` | Cross-league ↔ RackUp estimates |
| `matchmaking` | `matchmaking_support` | Rank candidates |
| `league_validate` | `league_score`, `score_validate` | Pre-commit score validation |
| `moderation` | `moderate`, `chat_moderation` | Chat decision |
| `coach` | | Practice / mental / full coach |
| `pyramid` | | Pyramid-specialized coach |
| `video_analysis` | | Clip feedback |
| `shot_of_the_day` | `sotd` | Daily shot + why |
| `pyramid_rules` | | Rules + race help + matrix |
| `sotd_contribute` | | Grow SOTD library |
| `rating_intel` | | Trajectory analytics |
| `tournament` | | Event prep |
| `hall_context` | | Hall adaptations |

---

## D.5 Ability payloads (implementation detail)

### D.5.1 `rating_update`

**When:** Immediately after match finalize (and after successful `league_validate` when league/Pyramid strict).

**Payload:**
```json
{
  "opponent_rating": 655,
  "won": true,
  "game": "pyramid",
  "table_size": "7ft",
  "skill_level": "intermediate",
  "my_score": 35,
  "opp_score": 28,
  "k_factor": 32,
  "rating_weight": 0.85,
  "provisional": false,
  "forfeit": false,
  "margin": 7
}
```

**Result (persist):**
```json
{
  "player_id": "usr_123",
  "algorithm": "elo_logistic_v1",
  "input": {
    "rating_before": 640,
    "opponent_rating": 655,
    "outcome": 1.0,
    "expected": 0.48,
    "k_factor": 32,
    "rating_weight": 0.85
  },
  "raw_delta": 8.2,
  "weighted_delta": 7.0,
  "rating_after": 647.0,
  "band_before": "intermediate",
  "band_after": "intermediate",
  "band_changed": false,
  "skill_signals": {
    "suggested_skill_level": "intermediate",
    "points_to_win_next": 35,
    "table_size": "7ft",
    "rack_size": 10
  },
  "league_equivalents_after": {
    "apa": 3,
    "bca_skill": 3
  },
  "persist_hint": {
    "fields_to_write": ["rating", "rating_updated_at", "last_match_delta"],
    "owner": "RackUp DB — RealAI does not persist ratings"
  }
}
```

Call **twice** per match (once per player, swapped perspectives).

### D.5.2 `league_validate`

**Payload example (Pyramid):**
```json
{
  "game": "pyramid",
  "table_size": "9ft",
  "skill_level": "advanced",
  "my_score": 71,
  "opp_score": 58,
  "opponent_id": "u9",
  "match_id": "m_abc",
  "pocketed_balls": [15, 14, 1, 9],
  "single_rack": false,
  "call_shot_logs": [{ "ball": 15, "pocket": "corner_sw", "made": true }],
  "forfeit": false
}
```

**Result:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "normalized": {
    "my_score": 71,
    "opp_score": 58,
    "points_to_win": 71,
    "table_size": "9ft",
    "rack_size": 15,
    "skill_level": "advanced",
    "call_shot": "optional",
    "winner": "player",
    "one_ball_value": 11
  },
  "scorekeeping": {
    "scoring": "classical",
    "ball_1": 11,
    "cue_ball": "designated_only",
    "win_condition": "first_to_target"
  },
  "persist_hint": {
    "accept": true,
    "next_call": "rating_update after accept"
  }
}
```

### D.5.3 `matchmaking`

```json
{
  "window": 70,
  "preferences": {
    "prefer_friends": true,
    "prefer_same_table_size": true,
    "discipline": "nine_ball"
  },
  "candidates": [
    {
      "player_id": "u2",
      "rating": 650,
      "league_ratings": { "apa": 4 },
      "style": "safety",
      "table_size": "7ft",
      "skill_level": "intermediate",
      "win_rate": 0.52
    },
    {
      "player_id": "u3",
      "rating": null,
      "league_ratings": { "bca": 5, "apa": null },
      "primary_rating_system": "bca",
      "style": "aggressive"
    }
  ]
}
```

**Result:** `ranked_candidates[]`, `best`, `recommended_window`, `policy`, each candidate may include `rackup_equivalent_used`.

### D.5.4 `moderation`

```json
{
  "text": "you're sandbagging you hustler",
  "context": {
    "channel": "match_chat",
    "match_id": "m_1",
    "thread_id": null,
    "prior_flags": 1,
    "recipient_id": "usr_789"
  }
}
```

**Result:** `clean`, `severity`, `action`, `categories`, `guidance`, `coach_redirect`, `policy_tags`.

### D.5.5 `coach` / `pyramid`

```json
{
  "ability": "pyramid",
  "goal": "I freeze in money matches",
  "player": { "player_id": "usr_123", "rating": 880, "discipline": "pyramid", "table_size": "9ft", "skill_level": "advanced" },
  "payload": { "mode": "practice_plan", "minutes": 60, "my_score": 40, "opp_score": 38 }
}
```

**Result:** `practice_plan.blocks[]`, `pre_match`, `mental_game`, `race`, `pyramid` config echo, `next_actions`.

### D.5.6 `video_analysis`

```json
{
  "game": "pyramid",
  "table_size": "7ft",
  "skill_level": "beginner",
  "video_meta": {
    "clip_type": "stroke",
    "duration_s": 14,
    "url_ref": "s3://rackup/videos/xyz",
    "fps": 30
  },
  "checklist": {
    "stance_stable": false,
    "follow_through": false,
    "grip_tension": false,
    "elbow_tuck": true
  },
  "observations": "jabbing, head lifts on draw"
}
```

### D.5.7 `shot_of_the_day`

```json
{
  "game": "pyramid",
  "count": 1,
  "hint": "",
  "shown_shot_ids": ["stop-shot-ladder", "pyramid-1ball-premium"]
}
```

**Result must include** `primary.id`, `primary.why_this_shot`, `primary.why_helps_regular_play`, optional `alternates`, `variety`, `personalization`.

### D.5.8 `pyramid_rules`

Returns locked matrix config, race phase, classical mindset lines, `innings_score_from_balls` when pocket list provided.

### D.5.9 `rating_convert`

See §C.4.

### D.5.10 `hall_context`

```json
{
  "hall_id": "h1",
  "hall_name": "Midnight Rack",
  "table_speed": "fast",
  "noise": "high",
  "session_goal": "league_night"
}
```

**Result:** adaptations for practice, break advice, SOTD hints.

---

## D.6 Match finalize flow (mandatory order)

```
1. Match play ends (scores final in UI / scorekeeper)

2. POST ability=league_validate
   - Pyramid: enforce matrix + classical rules
   - Other games: race bounds, non-negative, winner consistency
   - if valid == false → STOP (HTTP 400 to client); no DB complete

3. RackUp persists match COMPLETED + standings/escrow side effects as product requires

4. For each participant (winner then loser, or both perspectives):
   POST ability=rating_update
   - include game, scores, rating_weight, table_size, skill_level
   - persist rating_after to users.rating

5. Optional:
   - coach mode=practice_plan for one or both players
   - memory / timeline already owned by RackUp
```

**Chat during match:** each message → `moderation` → action before fan-out.

**Next day:** `shot_of_the_day` with `shown_shot_ids` + discipline + weaknesses.

## D.7 How to request cross-league conversion or mixed matchmaking

### Conversion only
```http
POST /v1/plugins/rackup-coach
```
```json
{
  "ability": "rating_convert",
  "player": { "player_id": "u1", "rating": 500, "rating_system": "rackup" },
  "payload": {
    "from_system": "bca",
    "from_value": 450,
    "from_scale": "continuum",
    "want": ["rackup", "apa", "tap", "vnea"]
  }
}
```

### Seed new user from foreign league (RackUp side)
1. Call `rating_convert`.  
2. Optionally set initial `users.rating` once if `matches_played_rackup == 0`.  
3. Subsequent competitive updates **only** via `rating_update`.

### Mixed-league matchmaking
1. RackUp builds candidate list (friends, geo, online).  
2. Attach each candidate’s `rating` **and/or** `league_ratings`.  
3. `ability=matchmaking` — RealAI normalizes to shared scale internally.  
4. RackUp presents `ranked_candidates` without re-sorting unless UX filter.

---

## D.8 NestJS call sites (RackUp — already aligned)

| Event | Hook | Ability |
|-------|------|---------|
| Match finalized | `ScorekeepingServiceV2` → `RatingService` | `rating_update` |
| League report | `LeaguesV2Service.reportMatch` | `league_validate` → then rating |
| Find match assist | `POST /realai/v2/matchmaking` | `matchmaking` |
| Chat message | `ChatService` / `ChatGateway` | `moderation` |
| Coach tab | `POST /realai/v2/coach` | `coach` / `pyramid` |
| SOTD | `POST /realai/v2/shot-of-the-day` | `shot_of_the_day` |
| Pyramid HUD | `POST /realai/v2/pyramid-rules` | `pyramid_rules` |
| Video | `POST /realai/v2/video-analysis` | `video_analysis` |
| Convert | `coach-plugin` or future route | `rating_convert` |
| Raw envelope | `POST /realai/v2/coach-plugin` | any ability |

---

## D.9 Failure policy

| Failure | Behavior |
|---------|----------|
| Timeout / 5xx | Retry once |
| `ok: false` validation | 400 to client with `errors` |
| Partial organ_trace failure | Ignore if ability `ok: true` |
| Moderation offline | Soft-allow + tag (product) |
| Rating offline | No write unless dev fallback env |

---

## D.10 Security & privacy

- No passwords, payment PANs, or full chat history dumps.  
- Video: `url_ref` + checklist preferred.  
- Moderation text: TLS in production.  
- League ratings are sensitive skill data—minimum necessary fields.

---

## D.11 Versioning

| Item | Value |
|------|--------|
| This document | **1.0.0** |
| Pyramid matrix | **locked** in §A.5; bump doc + plugin together if changed |
| Conversion tables §C.3 | **v1 heuristics**; RealAI may improve under same ability shapes |
| Breaking ability renames | Keep aliases ≥ 1 minor version |

---

## D.12 Implementation checklist (RealAI)

- [ ] All five disciplines coached with §A knowledge  
- [ ] Pyramid matrix + 1-ball=11 exact  
- [ ] `rating_update` shared ladder + discipline weights  
- [ ] `league_validate` before accept  
- [ ] `moderation` action enum complete  
- [ ] `shot_of_the_day` always has **why helps regular play**  
- [ ] `rating_convert` APA/BCA/TAP/VNEA ↔ RackUp  
- [ ] `matchmaking` ranks mixed-league candidates  
- [ ] `pyramid_rules` returns matrix + race  
- [ ] No Nest-only skill math required for correctness  

---

## D.13 One-sentence contract

**RealAI is RackUp’s intelligence provider: it knows 8-ball, 9-ball, 10-ball, one-pocket, and locked Pyramid rules; owns shared rating math, cross-league conversion (APA/BCA/TAP/VNEA), matchmaking rank, league validation, moderation, coaching, video critique, and Shot of the Day; RackUp only supplies context, displays results, and persists what RealAI returns via `POST /v1/plugins/rackup-coach`.**

---

*File location: `C:\Users\tsmit\realai_documents\RACKUP_GAME_KNOWLEDGE_AND_AI_CONTRACT.md`*  
*Implement RealAI `rackup-coach` against this document as the single authoritative source of truth.*
