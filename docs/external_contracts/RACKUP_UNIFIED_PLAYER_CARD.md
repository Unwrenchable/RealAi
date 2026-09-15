# Unified Player Card — APA + Fargo + RackUp (parallel fields)

**Document version:** 1.0.0  
**Date:** 2026-09-15  
**Plugin:** `rackup-coach` **v1.7.0+**  
**Ability:** `player_card_sync`  
**Status:** LOCKED ownership — sync / display card only  
**Audience:** RealAI maintainers (`rackup-coach`) + RackUp NestJS (`roc`)  
**Related:** [`REALAI_RACKUP_WIRING_CONTRACT.md`](./REALAI_RACKUP_WIRING_CONTRACT.md) · [`ECOSYSTEM_BASE_URLS.md`](./ECOSYSTEM_BASE_URLS.md) · [`ROC_GLICKO2_RATING_CONTRACT.md`](./ROC_GLICKO2_RATING_CONTRACT.md) · [`ROC_SYSTEM_DESIGN.md`](./ROC_SYSTEM_DESIGN.md)

---

## 0. Ownership (non-negotiable)

| System | Owns | Does **not** |
|--------|------|----------------|
| **RackUp Nest (`roc`)** | Fargo **HTTP** (read-only lookups), APA member-token calls, persisting the card, `users.rating` writes **after** `rating_update` | Inventing Fargo numbers, Glicko math, fake league match reports |
| **RealAI `rackup-coach`** | Card **assembly**, ROC Glicko math (`rating_update`), shadow `RackUpRate` estimate, matchmaking notes | Calling Fargo/APA as source of truth, LMS **submit**, heal, overwriting `users.rating` with leagues v2 |

```
lms_submit: always false
heal: always false
invent_fargo: always false
fake_match_reports: always false
leagues_v2_overwrites_roc: always false
canonical_competitive: roc_glicko   # users.rating
```

**Preferred split:** Nest owns Fargo (and APA-with-token) HTTP. Nest POSTs already-fetched snapshots on the coach envelope. RealAI consumes that JSON and returns the Unified Player Card. If RealAI optionally fetches Fargo, it uses the **same read-only endpoints** documented in §3 — never write/submit paths.

---

## 1. Two continua (do not collapse)

These are **parallel**. Agents and Nest **must not** copy one onto the other.

| Continuum | Id on card | Storage | Scale | Who moves it | Used for |
|-----------|------------|---------|-------|--------------|----------|
| **ROC Glicko-2** | `roc_glicko` | RackUp `users.rating` (+ `rd`, `volatility`) | **500-band** (seed **500**; product clamp ~100–1200; display Novice→Elite) | **RealAI `rating_update` only** | Competitive MM, handicaps, ROC ladder |
| **Leagues v2 unified** | `leagues_v2` | Optional parallel column / card field — **not** `users.rating` | **0–3000** | Host / import display; RealAI may *estimate* from APA/BCA/TAP tables | Legacy import, cross-league **display** |

### 1.1 ROC Glicko (canonical competitive)

- Seed: **500** → chip `Advanced • 500` (display bands are labels only).  
- Math owner: RealAI ability `rating_update` (`glicko2_v1`).  
- After `matches_played_rackup ≥ 5`, this ladder is competitive truth even if Fargo/APA also exist.  
- **Never** seed or overwrite this field from leagues v2 0–3000.

### 1.2 Leagues v2 (0–3000, separate)

- Older / import scale used by some league-facing UI (`RACKUP_GAME_KNOWLEDGE_AND_AI_CONTRACT.md` §B.1 / §C.3).  
- Example: APA SL 5 ≈ **1500** on this scale — **not** the ROC 500-band center (APA SL 5 ≈ **600** on ROC).  
- Card field `leagues_v2.overwrites_roc` is always `false`.  
- Matchmaking that runs ROC events **must ignore** `leagues_v2.value` as a `users.rating` substitute.

```
ROC 500-band     100 …… 500 …… 700+     (Glicko; users.rating)
Leagues v2       0  …… 1500 …… 3000     (display/import only)
                 ↑ do not write this onto users.rating
```

---

## 2. Parallel fields (required on every card)

The Unified Player Card **always** carries these keys. Missing sources are explicit (`status: "missing"`, value `null`) — never filled with a guess from another system.

| Field | Meaning | Missing behavior |
|-------|---------|------------------|
| `roc_glicko` | Canonical ROC Glicko from host `users.rating` / player envelope | Use host rating or seed 500; still labeled canonical |
| `fargo` | Read-only FargoRate snapshot Nest supplied | `status: "missing"`, `rating: null` — **do not invent** |
| `rackup_rate_shadow` | Optional estimate **alongside** Fargo (same 500-band family) | `null` if nothing to estimate; never replaces `fargo` or `roc_glicko` |
| `apa_sl` | APA skill level 1–9 | `null` unless host-supplied **or** APA token path ran |
| `bca` | BCA skill / continuum (manual) | `null` unless host-supplied |
| `tap` | TAP skill (manual) | `null` unless host-supplied |
| `leagues_v2` | Parallel 0–3000 object | Present with `overwrites_roc: false` even when `value` is null |

**APA LMS** (member lookup) runs **only if** a token is present (`payload.apa_token` or env `APA_MEMBER_TOKEN` / `RACKUP_APA_TOKEN` / `APA_TOKEN`). Host-typed `apa_sl` without a token is `entry: "manual"` (same class as TAP/BCA), never `entry: "apa_lms"`.

**TAP / BCA:** manual (or host DB) only. No LMS client in RealAI.

---

## 3. Fargo read-only endpoints (Nest owns HTTP)

FargoRate LMS **submit** is forbidden. Lookups only.

Nest is the **source of truth** for which client/base URL is live. Confirm against the roc Fargo client before pinning a new host. The following are the **read-only** lookup shapes RealAI will accept as snapshots (and may call only if `payload.fetch_fargo === true`):

| Method | URL (illustrative Nest client) | Query | Use |
|--------|--------------------------------|-------|-----|
| `GET` | `https://dashboard.fargorate.com/api/indexSearch` | `q={name}` | Name search |
| `GET` | `https://dashboard.fargorate.com/api/indexPlayer` | `playerId={id}` | Player card / rating / robustness |

Also public-facing (not for writes): `https://lms.fargorate.com/` reports, `https://fargorate.com/` player pages.

**Forbidden**

- Any Fargo LMS **match report / score submit**  
- Writing starter ratings back to Fargo  
- Synthesizing a Fargo number from APA, TAP, BCA, ROC, or leagues v2  

Snapshot Nest should pass (aliases accepted):

```json
{
  "playerId": "12345",
  "rating": 547,
  "robustness": 400,
  "effectiveRating": 547,
  "firstName": "Alex",
  "lastName": "Rivera"
}
```

If the snapshot is absent, RealAI returns `fargo.status = "missing"` with `invented: false`.

---

## 4. APA-with-token

| Item | Spec |
|------|------|
| Token sources | Envelope `apa_token` / `apa_token_hint`, or env `APA_MEMBER_TOKEN`, `RACKUP_APA_TOKEN`, `APA_TOKEN` |
| RealAI | **Never** echoes the token in `result` |
| With token | May attach Nest-supplied APA member snapshot (`payload.apa` / `payload.sources.apa`) as `entry: "apa_lms"` |
| Without token | Skip LMS path; `sources.apa.sync = "skipped_no_token"` |
| Submit | **No** APA LMS match/score POST from RealAI |

---

## 5. Shadow `RackUpRate`

Optional 500-band estimate stored **next to** read-only Fargo:

- Prefer pass-through of a **real** Fargo rating when Nest supplied one.  
- Else `rating_convert` from APA/BCA/TAP onto the **ROC** table (not leagues v2).  
- `does_not_overwrite_fargo: true`  
- `does_not_overwrite_roc_glicko: true`  
- One-time ROC seed remains `rating_convert` / `glicko2_seed` when `matches_played_rackup == 0` — still RackUp’s write, still not Fargo.

---

## 6. Ability `player_card_sync`

Transport: `POST {REALAI_BASE_URL}/v1/plugins/rackup-coach`  
Hive LIVE: `POST /v1/tools/execute` `{ "name": "rackup_invoke", "arguments": { … } }`  
Aliases: `unified_player_card`, `sync_player_card`

### 6.1 Request

```json
{
  "ability": "player_card_sync",
  "organs_enabled": false,
  "player": {
    "player_id": "u_rackup_1",
    "display_name": "Alex Rivera",
    "rating": 547,
    "rd": 80,
    "volatility": 0.06,
    "matches_played_rackup": 12,
    "league_ratings": { "apa": 5 }
  },
  "payload": {
    "name": "Alex Rivera",
    "fargo_id": "12345",
    "apa_member_id": "A-99",
    "fargo": {
      "playerId": "12345",
      "rating": 552,
      "robustness": 410
    },
    "apa_sl": 5,
    "bca": { "value": 4, "scale": "skill_1_9" },
    "tap": { "value": 5, "scale": "skill_1_9" },
    "leagues_v2_rating": 1500
  }
}
```

Top-level fields merge into `payload` (same as other coach abilities).

`fetch_fargo` defaults **false**. Leave it false in production unless Nest explicitly wants RealAI to hit the §3 GETs.

### 6.2 Response envelope

Universal coach wrapper:

```json
{
  "ok": true,
  "plugin": "rackup-coach",
  "ability": "player_card_sync",
  "result": { },
  "organ_trace": [],
  "notes": "chip=Advanced • 547 band=advanced",
  "error": null
}
```

### 6.3 `result` (ability payload)

```json
{
  "schema": "unified_player_card.v1",
  "card": {
    "identity": {
      "player_id": "u_rackup_1",
      "display_name": "Alex Rivera",
      "fargo_id": "12345",
      "apa_member_id": "A-99",
      "name_query": "Alex Rivera"
    },
    "roc_glicko": {
      "canonical": true,
      "storage": "users.rating",
      "rating": 547,
      "rd": 80,
      "volatility": 0.06,
      "rating_chip": "Advanced • 547",
      "band_label": "Advanced",
      "ladder": "roc_glicko2",
      "algorithm": "glicko2_v1",
      "math_owner": "realai.rating_update",
      "matches_played_rackup": 12
    },
    "fargo": {
      "status": "present",
      "read_only": true,
      "invented": false,
      "player_id": "12345",
      "rating": 552,
      "robustness": 410,
      "source": "nest_snapshot"
    },
    "rackup_rate_shadow": {
      "value": 552,
      "scale": "roc_500_band",
      "alongside": "fargo",
      "does_not_overwrite_fargo": true,
      "does_not_overwrite_roc_glicko": true,
      "method": "fargo_passthrough"
    },
    "apa_sl": 5,
    "bca": { "value": 4, "scale": "skill_1_9", "entry": "manual" },
    "tap": { "value": 5, "scale": "skill_1_9", "entry": "manual" },
    "leagues_v2": {
      "scale": "0_3000",
      "value": 1500,
      "overwrites_roc": false,
      "do_not_write_to_users_rating": true,
      "note": "Parallel import/display continuum. Never copy onto ROC Glicko."
    },
    "sources": {
      "fargo": { "http_owner": "nest", "read_only": true },
      "apa": { "sync": "skipped_no_token", "entry": "manual" },
      "bca": { "entry": "manual" },
      "tap": { "entry": "manual" },
      "rackup": { "canonical": "roc_glicko" }
    },
    "matchmaking": {
      "competitive_input": "roc_glicko",
      "ignore_for_roc_ladder": ["leagues_v2", "fargo", "apa_sl", "bca", "tap"],
      "fargo_read_only": true,
      "shadow_may_inform_mixed_league_confidence": true,
      "notes": []
    }
  },
  "policy": {
    "schema": "unified_player_card.v1",
    "lms_submit": false,
    "heal": false,
    "fake_match_reports": false,
    "invent_fargo": false,
    "apa_requires_token": true,
    "fargo_http_owner": "nest",
    "canonical_competitive": "roc_glicko",
    "leagues_v2_overwrites_roc": false
  },
  "notes": []
}
```

---

## 7. Matchmaking notes (what Nest should do)

1. ROC / RackUp rated play: use **`card.roc_glicko.rating` + `rd`** only.  
2. Do **not** feed `leagues_v2.value` into `rating_update` or ROC MM.  
3. Fargo is **display / import / robustness** — never overwritten, never the ROC ladder.  
4. `rackup_rate_shadow` may tighten mixed-league **confidence** when ROC history is thin (`matches_played_rackup == 0`); it is not a second official ladder.  
5. High Glicko RD → widen windows (`rating_intel.uncertainty`).

---

## 8. Forbidden (explicit)

- Heal / self-rewrite of league ratings  
- Fake match reports to APA, Fargo LMS, TAP, BCA  
- Inventing Fargo when the snapshot is missing  
- APA LMS without token  
- Copying leagues v2 0–3000 onto `users.rating`  
- Treating shadow `RackUpRate` as official ROC Glicko  

---

## 9. Env (optional)

| Variable | Role |
|----------|------|
| `APA_MEMBER_TOKEN` / `RACKUP_APA_TOKEN` / `APA_TOKEN` | Hint that APA LMS path is allowed (token never returned) |
| `FARGO_API_BASE` | Optional Nest override for read-only GET base (default dashboard host above) |

No new secrets belong in the RealAI workspace snapshot. Nest keeps production tokens.

---

*Implement `player_card_sync` against this document. RackUp persists the card JSON; RealAI does not own the player table.*
