# RealAI ↔ RackUp Wiring Contract

**Document version:** 1.1.0  
**Date:** 2026-08-05  
**Audience:** RackUp NestJS engineers (integration) + RealAI maintainers  
**RealAI branch:** `unification/ultimate-all` (rackup-coach **v1.4.0** — ROC formats + continuous BCA-style rating + cross-league convert)  
**Related:** `ROC_SYSTEM_DESIGN.md`, `REALAI_ROC_ALIGNMENT_REPORT.md`  
**Purpose:** Production bridge so RackUp runs **all player-level intelligence** on RealAI as its **Intelligence Provider**.

---

## 0. System boundary (non-negotiable)

| System | Owns | Does **not** own |
|--------|------|------------------|
| **RealAI** | Algorithms, coaching intelligence, moderation decisions, rating **calculation**, matchup **signals**, Pyramid **rules/scoring math**, video **analysis structure**, Shot of the Day **generation & variety logic** | UI, NestJS routes as product surface, Postgres/Prisma, WebSockets fanout, auth sessions, friend graph storage, hall booking persistence |
| **RackUp** | App UI, NestJS API, database, WebSockets, halls, friends, match lifecycle, storing ratings after RealAI computes them, delivering chat, storing video blobs | Inventing skill math, reimplementing Pyramid rules, coaching content, moderation ML |

**Relationship:** RealAI does **not** “live alongside” RackUp as an optional feature.  
RealAI is the **intelligence provider** that powers player-level AI **inside** RackUp.  
RackUp **calls** RealAI; RackUp **persists** results RealAI returns.

```
┌─────────────────────────────────────────────────────────┐
│  RackUp (NestJS + DB + WS + UI)                         │
│  - auth, halls, friends, match records, media storage   │
│  - calls RealAI for every intelligence decision         │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTPS JSON
                           ▼
┌─────────────────────────────────────────────────────────┐
│  RealAI (OpenAI-compatible provider + rackup-coach)     │
│  - organs hive, rating math, moderation, coach, SOTD    │
│  - Pyramid rules engine, league validation              │
│  - NO NestJS, NO app DB writes                          │
└─────────────────────────────────────────────────────────┘
```

---

## 1. Transport & endpoints

### 1.1 Base URL

```
REALAI_BASE_URL=http://<realai-host>:8000
```

Default local: `http://127.0.0.1:8000`

### 1.2 Primary intelligence entry (recommended)

| Method | Path | Use |
|--------|------|-----|
| `POST` | `/v1/plugins/rackup-coach` | **Canonical** — all rackup abilities |
| `POST` | `/v1/rackup/coach` | Alias of above |

### 1.3 Organs / hive (optional advanced)

| Method | Path | Use |
|--------|------|-----|
| `GET` | `/v1/organs` | List organs |
| `GET` | `/v1/hive` | Living stack status |
| `POST` | `/v1/organs/invoke` | Call a single organ (incl. `organ.rackup-coach`) |
| `POST` | `/v1/organs/pipeline` | Ordered organ pipeline |
| `POST` | `/v1/chat/completions` | General LLM chat (organs enrich by default) |

### 1.4 Headers

```http
Content-Type: application/json
Authorization: Bearer <optional-provider-key>   # only if routing to external models
X-Provider: realai                              # optional; local-first default
X-RealAI-Organs: 1                              # 0 to disable organ enrichment on /v1/chat
X-Request-Id: <uuid>                            # RackUp correlation id (recommended)
X-RackUp-Tenant: <tenant-or-env>                # optional multi-env
```

RealAI **does not require** RackUp user JWTs. RackUp authenticates end users; RealAI trusts the **service** call from NestJS (use network policy / shared service token if exposed beyond localhost).

### 1.5 Python (same contract)

```python
from plugins.rackup_coach import invoke
result = invoke({ "ability": "...", "player": {...}, "payload": {...} })
```

```python
from modules.organs import call_organ
call_organ("organ.rackup-coach", goal="...", payload={...})
```

---

## 2. Universal request envelope

Every major ability uses this shape against `POST /v1/plugins/rackup-coach`:

```json
{
  "ability": "string",
  "goal": "optional free-text intent",
  "organs_enabled": true,
  "player": {
    "player_id": "uuid-or-stable-id",
    "display_name": "Alex",
    "rating": 640.0,
    "rating_system": "rackup",
    "discipline": "pyramid",
    "preferred_hand": "right",
    "weaknesses": ["cue_ball_control", "position_play"],
    "strengths": ["long_potting"],
    "recent_results": [
      {
        "opponent_id": "u2",
        "opponent_rating": 610,
        "won": false,
        "discipline": "pyramid",
        "table_size": "7ft",
        "skill_level": "intermediate",
        "my_score": 28,
        "opp_score": 35,
        "played_at": "2026-08-05T12:00:00Z"
      }
    ],
    "session_stats": {
      "balls_made": 42,
      "scratches": 2,
      "safeties": 5,
      "innings": 12
    },
    "history_notes": ["loses shape after long pots"],
    "hall_id": "hall_123",
    "hall_name": "Main St Billiards",
    "table_speed": "medium",
    "locale": "en",
    "table_size": "7ft",
    "skill_level": "intermediate",
    "pyramid_skill": "intermediate",
    "pyramid_score": 0,
    "pyramid_opp_score": 0
  },
  "payload": {}
}
```

### 2.1 Universal response envelope

```json
{
  "ok": true,
  "plugin": "rackup-coach",
  "ability": "shot_of_the_day",
  "result": { },
  "organ_trace": [
    {
      "organ_id": "organ.cerebellum",
      "ok": true,
      "notes": "linked ...",
      "output": {}
    }
  ],
  "notes": "band=intermediate rating=640",
  "error": null
}
```

| Field | Type | Meaning |
|-------|------|---------|
| `ok` | bool | Ability succeeded |
| `ability` | string | Echo of requested ability |
| `result` | object | **Ability-specific payload for RackUp UI/DB** |
| `organ_trace` | array | Debug / audit (optional to store) |
| `error` | string\|null | Machine-readable failure |

**HTTP status:** `200` with `ok:false` may still be returned for validation failures inside body; NestJS should treat transport errors (5xx/network) separately from `result.errors` / `ok:false`.

---

## 3. Context RackUp must pass (by domain)

| Context | Fields | Used by |
|---------|--------|---------|
| **Identity** | `player_id`, `display_name` | All |
| **Skill** | `rating`, `skill_level` / `pyramid_skill`, `rating_system` | Rating, matchmaking, coach, SOTD, Pyramid |
| **Game mode** | `discipline` (`pyramid`\|`eight_ball`\|…), `table_size` (`7ft`\|`9ft`) | Pyramid, SOTD, coach, league |
| **History** | `recent_results[]`, `weaknesses[]`, `strengths[]`, `history_notes[]` | Coach, SOTD, matchmaking, rating intel |
| **Live match** | `pyramid_score`, `pyramid_opp_score`, `payload.my_score`, `opp_score` | Pyramid race coaching, league validate |
| **Hall** | `hall_id`, `hall_name`, `table_speed`, hall cloth/noise in payload | Hall context, SOTD |
| **Social/chat** | message text, channel, prior flags | Moderation |
| **Media** | `video_meta`, checklist, observations (not raw bytes required) | Video analysis |
| **Variety** | `payload.shown_shot_ids[]` | SOTD anti-repeat |
| **Candidates** | `payload.candidates[]` | Matchmaking |
| **Friends (optional)** | pass as candidates filter or soft preference flags | Matchmaking (RackUp filters list first) |

**Rule:** RealAI never queries RackUp’s DB. If history matters, **RackUp must include it** in `player` / `payload`.

---

## 4. Ability contracts (production)

### 4.1 Rating update after a match  
**`ability`: `rating_update`** (aliases: `skill_update`, `post_match_rating`)

**When RackUp calls:** Immediately after a match is finalized (and league validate passed if league).

**Organs:** prefrontal-cortex, long-term-memory, intuition, neuroplasticity.

**Request `payload`:**

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
  "provisional": false,
  "forfeit": false,
  "margin": 7
}
```

Or omit `won` and use scores only (Pyramid first-to-target inference).

**Response `result` (consume & persist):**

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
  "pyramid": { },
  "persist_hint": {
    "fields_to_write": ["rating", "rating_updated_at", "last_match_delta"],
    "owner": "RackUp DB — RealAI does not persist ratings"
  }
}
```

**RackUp must:**

1. Write `rating_after` to `users.rating` (or skill table).  
2. Optionally store `weighted_delta`, `band_after`.  
3. **Never** recompute rating in NestJS.

**Pyramid weight:** Beginner 0.7×, Intermediate 0.85×, Advanced 1.0×, Pro 1.15× applied to Elo delta.

---

### 4.2 Suggested matchups / smart matchmaking  
**`ability`: `matchmaking`** (alias: `matchmaking_support`)

**When:** Find Match, challenge suggestions, league pairing assist.

**Organs:** frontal-cortex, intuition, semantic-memory, consciousness.

**Request `payload`:**

```json
{
  "window": 70,
  "candidates": [
    {
      "player_id": "u2",
      "rating": 650,
      "style": "safety",
      "table_size": "7ft",
      "skill_level": "intermediate",
      "win_rate": 0.52
    },
    {
      "player_id": "u3",
      "rating": 800,
      "style": "aggressive",
      "table_size": "9ft",
      "skill_level": "advanced"
    }
  ]
}
```

**Player** should include `table_size`, `skill_level`, `discipline`, `recent_results`.

**Response `result`:**

```json
{
  "player_id": "usr_123",
  "player_rating": 640,
  "band": "intermediate",
  "pyramid": {
    "table_size": "7ft",
    "rack_size": 10,
    "points_to_win": 35,
    "skill_level": "intermediate",
    "rating_weight": 0.85
  },
  "recommended_window": [-82.3, 82.3],
  "ranked_candidates": [
    {
      "player_id": "u2",
      "rating": 650,
      "fit_score": 118.5,
      "rating_delta": 10,
      "weighted_rating_delta": 8.5,
      "in_window": true,
      "notes": "..."
    }
  ],
  "best": { "player_id": "u2", "fit_score": 118.5 },
  "policy": {
    "prefer_same_table_size": "7ft",
    "prefer_same_skill_level": "intermediate",
    "rating_weight": 0.85,
    "points_to_win": 35
  }
}
```

**RackUp must:** Supply pre-filtered candidates (friends, online, same region). RealAI only ranks / scores.

---

### 4.3 League score submission / validation  
**`ability`: `league_validate`** (aliases: `league_score`, `score_validate`)

**When:** Before committing a league/Pyramid result to DB.

**Organs:** guardian, prefrontal, architecture-memory, semantic-memory.

**Request `payload`:**

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
  "call_shot_logs": [
    { "ball": 15, "pocket": "corner_sw", "made": true }
  ],
  "forfeit": false
}
```

**Response `result`:**

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
    "owner": "RackUp DB writes only if valid==true",
    "next_call": "rating_update after accept"
  }
}
```

**RackUp must:**

1. If `valid === false` → reject submission; show `errors[]`.  
2. If `valid === true` → persist scores; then call **`rating_update`**.  
3. Use `normalized.winner` for standings.

**Pyramid validation rules RealAI enforces:**

- Target from skill × table matrix  
- Neither below target → invalid (unless forfeit)  
- Both ≥ target → invalid  
- Ball numbers must fit rack (1–10 or 1–15)  
- Classical: 1-ball value 11  

---

### 4.4 Chat moderation  
**`ability`: `moderation`** (aliases: `moderate`, `chat_moderation`)

**When:** On every chat message (or sampled + reported); before broadcast.

**Organs:** amygdala, guardian, prefrontal, paradox, short-term-memory.

**Request:**

```json
{
  "ability": "moderation",
  "player": { "player_id": "usr_456", "rating": 720 },
  "payload": {
    "text": "you're sandbagging you hustler",
    "context": {
      "channel": "match_chat",
      "match_id": "m_1",
      "prior_flags": 1,
      "recipient_id": "usr_789"
    }
  }
}
```

**Response `result`:**

```json
{
  "text_preview": "you're sandbagging you hustler",
  "player_id": "usr_456",
  "clean": false,
  "severity": 3,
  "severity_label": "elevated",
  "action": "warn_and_flag",
  "guidance": "Warn user; flag for trust & safety (rating integrity).",
  "categories": {
    "sandbagging_accusation": true
  },
  "matched_patterns": { "sandbagging_accusation": 1 },
  "coach_redirect": "Redirect players to rating appeal flow...",
  "policy_tags": ["sandbagging_accusation"]
}
```

**`action` enum (RackUp switch):**

| action | RackUp behavior |
|--------|-----------------|
| `allow` | Deliver message |
| `soft_filter` | Deliver + soft nudge / rate-limit |
| `warn` | Deliver or hold per policy + warn |
| `warn_and_flag` | Warn + create T&S flag |
| `hold_for_review` | Do not deliver; queue human review |
| `block_and_escalate` | Drop message; escalate |

---

### 4.5 Professional coaching / practice plan  
**`ability`: `coach`** or **`pyramid`**

**When:** Coach tab, post-match “what to practice,” pre-match prep.

**Organs:** frontal, prefrontal, cerebellum, procedural/episodic memory, limbic, intuition.

**Request:**

```json
{
  "ability": "pyramid",
  "goal": "I freeze in money matches",
  "player": {
    "player_id": "usr_123",
    "rating": 880,
    "discipline": "pyramid",
    "table_size": "9ft",
    "skill_level": "advanced",
    "weaknesses": ["match_pressure", "safety_play"]
  },
  "payload": {
    "mode": "pyramid",
    "minutes": 60,
    "my_score": 40,
    "opp_score": 38
  }
}
```

**`payload.mode`:** `full` \| `practice_plan` \| `pre_match` \| `mental` \| `pattern` \| `pyramid`

**Response `result` (key fields):**

```json
{
  "band": "advanced",
  "pyramid": {
    "table_size": "9ft",
    "rack_size": 15,
    "points_to_win": 71,
    "call_shot": "optional",
    "rating_weight": 1.0
  },
  "practice_plan": {
    "duration_minutes": 60,
    "blocks": [
      { "order": 1, "skill": "point_counting", "minutes": 10, "drill": "..." }
    ]
  },
  "pre_match": { "warmup": [], "checklist": [] },
  "mental_game": { "cues": [], "pressure_protocol": [] },
  "pattern_recognition": [],
  "classical_mindset": [],
  "race": {
    "target": 71,
    "my_points_needed": 31,
    "phase": "midgame"
  },
  "next_actions": []
}
```

**RackUp UI:** Render plan blocks as checklist; store completion optionally in DB.

---

### 4.6 Video analysis  
**`ability`: `video_analysis`**

**When:** After player uploads stroke/stance/break clip.

**Organs:** cerebellum, sensory, procedural, frontal, prefrontal.

**Important:** RealAI does **not** require binary video in-process. RackUp stores media; send **metadata + checklist + observations** (from client CV, coach notes, or human tags).

**Request `payload`:**

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

**Response `result`:**

```json
{
  "findings": [
    { "area": "stroke", "finding": "...", "fix": "..." }
  ],
  "recommended_drills": ["..."],
  "expectation": "Pyramid 7ft/10-ball · skill=beginner · first to 25. ...",
  "pyramid": { "points_to_win": 25, "rack_size": 10 },
  "scorecard": { "issue_count": 3, "ready_for_match_sim": false },
  "next_upload_prompt": "..."
}
```

**RackUp:** Attach `result` to video record; show drills as tasks.

---

### 4.7 Shot of the Day  
**`ability`: `shot_of_the_day`** (alias: `sotd`)

**When:** Daily card, home feed, post-login.

**Organs:** cerebellum, creativity furnace, procedural/episodic memory, hippocampus, intuition.

**Request `payload`:**

```json
{
  "game": "pyramid",
  "count": 1,
  "hint": "",
  "shown_shot_ids": ["stop-shot-ladder", "pyramid-1ball-premium"]
}
```

**Player** should include `weaknesses`, `discipline`, `table_size`, `skill_level`, `recent_results`.

**Response `result`:**

```json
{
  "date_role": "shot_of_the_day",
  "coaching_line": "Pyramid 7ft/10-ball · first to 35 · ...",
  "primary": {
    "id": "pyramid-10ball-value-route",
    "title": "Pyramid 7ft/10-ball: high-value two-ball route",
    "setup": "...",
    "objective": "...",
    "why_this_shot": "...",
    "why_helps_regular_play": "Builds transferable skills for regular match play...",
    "targets_weaknesses": ["pattern_play", "position_play"],
    "reps": 12,
    "success_metric": "...",
    "pro_tip": "...",
    "not_a_trick_shot": true
  },
  "alternates": [],
  "pyramid": { "rack_size": 10, "points_to_win": 35 },
  "personalization": {
    "avoided_recent_ids": ["stop-shot-ladder"]
  },
  "variety": {
    "library_size_static": 15,
    "library_size_grown": 0,
    "policy": { "rules": ["..."] }
  }
}
```

**RackUp must:**

1. Display `primary` + `why_helps_regular_play` (required UX copy).  
2. Persist `primary.id` per user/day for variety (`shown_shot_ids` next call).  
3. Never invent shots client-side.

---

### 4.8 Pyramid rules / mid-game scoring help  
**`ability`: `pyramid_rules`**

**When:** Match HUD, rules screen, scorekeeper assist.

**Organs:** frontal, semantic, architecture, prefrontal.

**Request:**

```json
{
  "ability": "pyramid_rules",
  "player": {
    "player_id": "usr_123",
    "table_size": "7ft",
    "skill_level": "pro",
    "discipline": "pyramid",
    "rating": 920
  },
  "payload": {
    "my_score": 41,
    "opp_score": 38,
    "pocketed_balls": [10, 9, 1]
  }
}
```

**Response `result`:**

```json
{
  "game": "RackUp Pyramid",
  "config": {
    "table_size": "7ft",
    "rack_size": 10,
    "skill_level": "pro",
    "points_to_win": 50,
    "call_shot": "yes",
    "rating_weight": 1.15,
    "one_ball_value": 11
  },
  "matrix": {
    "skill_matrix": [
      {
        "skill_level": "beginner",
        "7ft_10ball_points": 25,
        "9ft_15ball_points": 40,
        "call_shot": "no",
        "rating_weight": 0.7
      }
    ]
  },
  "race": {
    "target": 50,
    "my_score": 41,
    "opp_score": 38,
    "my_points_needed": 9,
    "phase": "endgame"
  },
  "classical_mindset": ["Count the table...", "1-ball is worth 11..."],
  "innings_score_from_balls": 30,
  "coaching_summary": "7ft → 10-ball rack | pro first to 50 | call_shot=yes | rating_weight=1.15×"
}
```

---

### 4.9 Grow Shot of the Day library  
**`ability`: `sotd_contribute`**

**When:** Coach/admin approves a new high-quality shot for the global library.

**Request `payload.shot`:**

```json
{
  "title": "Soft stun to short-rail zone",
  "setup": "...",
  "objective": "...",
  "why": "Improves lag shape for 8-out and Pyramid value routes",
  "weaknesses": ["position_play"],
  "bands": ["intermediate", "advanced"],
  "discipline": ["pyramid", "eight_ball"],
  "reps": 20,
  "pyramid_rack": [10, 15]
}
```

**Response:** `{ "ok": true, "id": "grown-...", "count": N }`  
Stored under `REALAI_DATA_DIR/rackup_coach/sotd_library.json` (provider-local growth).  
RackUp should still keep a DB log of contributions.

---

## 5. Locked Pyramid rules (authoritative)

Implemented in `plugins/rackup_coach/pyramid.py`.

| Skill | 7 ft points (10-ball) | 9 ft points (15-ball) | Call shot | Rating weight |
|-------|----------------------|----------------------|-----------|---------------|
| Beginner | 25 | 40 | No | 0.7× |
| Intermediate | 35 | 55 | No | 0.85× |
| Advanced | 45 | 71 | Optional | 1.0× |
| Pro | 50 | 71 | Yes | 1.15× |

- **Table → rack:** 7ft → 10 balls; 9ft → 15 balls  
- **Scoring:** ball N scores N; **1-ball = 11**; designated cue ball only  
- **Win:** first to skill×table target  

RackUp **must not** hardcode a conflicting matrix; treat RealAI `pyramid_rules` / `config` as source of truth at runtime (or pin this table in both places and version-bump together).

---

## 6. Shot of the Day variety & growth (how it scales)

| Mechanism | Owner | Behavior |
|-----------|--------|----------|
| Static catalog | RealAI code (`_SHOT_LIBRARY`) | Core quality shots + Pyramid variants |
| Grown catalog | RealAI disk (`~/.realai/rackup_coach/sotd_library.json`) | `sotd_contribute` appends coach-approved shots |
| Per-player history | RealAI disk + **RackUp DB** | Avoid re-showing last ~14 IDs |
| Host `shown_shot_ids` | RackUp | Cross-device variety (send on every SOTD call) |
| Scoring | RealAI | Weakness + skill + Pyramid rack fit − variety penalty |
| Copy requirement | Both | Always surface `why_helps_regular_play` / `why_this_shot` |

**RackUp daily job (recommended):**

1. For each active user (or cohort), call `shot_of_the_day` with history + weaknesses.  
2. Cache card in Redis/DB for 24h.  
3. Append `primary.id` to user’s `shown_shot_ids`.

---

## 7. Organs map (internal RealAI)

| Ability | Primary organs |
|---------|----------------|
| rating_update | prefrontal, long-term-memory, intuition, neuroplasticity |
| matchmaking | frontal, intuition, semantic, consciousness |
| league_validate | guardian, prefrontal, architecture, semantic |
| moderation | amygdala, guardian, prefrontal, paradox, STM |
| coach / pyramid | frontal, prefrontal, cerebellum, procedural/episodic, limbic, intuition |
| video_analysis | cerebellum, sensory, procedural, frontal, prefrontal |
| shot_of_the_day | cerebellum, creativity furnace, procedural/episodic, hippocampus, intuition |
| pyramid_rules | frontal, semantic, architecture, prefrontal |
| sotd_contribute | creativity furnace, procedural, cerebellum |
| organ.rackup-coach | Meta organ → full plugin invoke |

---

## 8. NestJS integration sketch

```ts
// realai.client.ts
export async function realaiCoach(body: RackUpCoachRequest): Promise<RackUpCoachResponse> {
  const res = await fetch(`${process.env.REALAI_BASE_URL}/v1/plugins/rackup-coach`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Request-Id': randomUUID(),
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new ServiceUnavailableException('RealAI unavailable');
  return res.json();
}
```

### Suggested NestJS call sites

| RackUp event | NestJS hook | ability |
|--------------|-------------|---------|
| Match finalized | `MatchesService.finalize` | `league_validate` → if ok → `rating_update` |
| Find match | `MatchmakingService.suggest` | `matchmaking` |
| Chat message | `ChatGateway.handleMessage` | `moderation` before broadcast |
| Coach tab | `CoachController.session` | `coach` / `pyramid` |
| Video processed | `VideosService.onUploaded` | `video_analysis` |
| Daily cron | `SotdJob.run` | `shot_of_the_day` |
| Score UI / HUD | `PyramidController.rules` | `pyramid_rules` |

### Failure policy

| Failure | RackUp behavior |
|---------|-----------------|
| RealAI timeout/5xx | Retry once; degrade gracefully (allow chat with delayed mod queue; block rating write until retry succeeds for rated matches) |
| `ok: false` validation | Return 400 to client with `result.errors` |
| Partial organ_trace failure | Ignore if ability `ok: true` |

---

## 9. End-to-end match flow (Pyramid)

```
1. Player A vs B start match
   RackUp loads pyramid_rules (or cached matrix) for table_size + skill_level

2. Live scoring in RackUp UI
   Optional: periodic pyramid_rules with my_score/opp_score for "points needed"

3. Match ends → NestJS:
   a. POST league_validate { my_score, opp_score, table_size, skill_level, ... }
   b. if !valid → reject
   c. persist match
   d. POST rating_update for A and for B (swap perspectives)
   e. persist rating_after for each
   f. optional: POST coach with mode=practice_plan for loser/winner

4. Chat during match
   Each message → moderation → action

5. Next day
   shot_of_the_day with discipline=pyramid + shown_shot_ids
```

---

## 10. Versioning & compatibility

| Item | Value |
|------|--------|
| Plugin | `rackup-coach` **1.1.0+** |
| Contract doc | **1.0.0** |
| Breaking change policy | Bump plugin version; keep aliases (`sotd`, `moderate`) |
| Matrix pin | Documented in §5; runtime authoritative via `pyramid_rules` |

RackUp should log `plugin` + RealAI git SHA / health in admin for support.

---

## 11. Security & privacy

- Send only **necessary** player fields (no passwords, no payment PANs).  
- Video: prefer `url_ref` + checklist; if frames sent later, use private URLs.  
- Moderation text may be sensitive — TLS only in production.  
- RealAI service should not be public without auth gateway.

---

## 12. Checklist for RackUp “fully on RealAI”

- [ ] All rated matches call `rating_update` (not local Elo)  
- [ ] League submissions call `league_validate` before DB write  
- [ ] Matchmaking UI uses `matchmaking` ranked list  
- [ ] Chat path uses `moderation` actions  
- [ ] Coach surfaces use `coach` / `pyramid`  
- [ ] Video review uses `video_analysis`  
- [ ] Daily SOTD uses `shot_of_the_day` + stores shown IDs + shows **why**  
- [ ] Pyramid matches use matrix from RealAI / this contract  
- [ ] No duplicate skill math in NestJS  

---

## 13. Quick reference — ability strings

| Ability string | Purpose |
|----------------|---------|
| `rating_update` | Post-match rating |
| `matchmaking` | Suggested opponents |
| `league_validate` | Score / league validation |
| `moderation` | Chat decision |
| `coach` / `pyramid` | Coaching & plans |
| `video_analysis` | Video feedback |
| `shot_of_the_day` | Daily shot + why |
| `pyramid_rules` | Rules + race help |
| `sotd_contribute` | Grow SOTD library |
| `rating_intel` | Trajectory analytics |
| `tournament` | Event prep |
| `hall_context` | Hall/session adaptations |

---

## 14. One-sentence contract

**RackUp is the product shell; RealAI is the intelligence provider — every skill change, matchup suggestion, league score check, moderation decision, coaching plan, video critique, Shot of the Day, and Pyramid scoring rule is computed by RealAI via `POST /v1/plugins/rackup-coach` with the envelopes in this document, and RackUp only displays and persists the results.**

---

## 15. ROC — Rack of Champions (v1.4 alignment)

**Full design:** `ROC_SYSTEM_DESIGN.md`  
**Alignment report:** `REALAI_ROC_ALIGNMENT_REPORT.md`  
**Plugin:** `rackup-coach` **v1.4.0**

| Topic | Spec |
|-------|------|
| Brand | ROC = competitive league system inside RackUp |
| Formats | `SINGLES` → `SCOTCH_DOUBLES` → `SCOTCH_JJ` → `TEAMS_5` |
| Game styles | `eight_ball`, `nine_ball`, `ten_ball`, `one_pocket`, `pyramid` |
| Rating | Continuous shared ladder (BCA/Fargo-like); chip `{Band} • {n}` e.g. Advanced • 547 |
| Display bands | Labels only — Novice / Intermediate / Advanced / Expert / Elite |
| Convert | `rating_convert` — APA/BCA/Fargo/TAP/VNEA → continuum |
| Finalize | `league_validate` → persist → `rating_update` (never reverse) |
| Ledger 45/35/20 | **RackUp only** — RealAI never posts money |
| Extra ability | `roc_info` — formats + provider boundary |

Pass on ROC calls when available: `format`, `game_style`, `roc_league_id`, `season_id`, `session_id`, `match_id`, `player_ids_json`, continuous `rating`, `league_ratings`.

---

*File location: `C:\Users\tsmit\realai_documents\REALAI_RACKUP_WIRING_CONTRACT.md`*  
*Feed this document as the integration prompt for the RackUp NestJS codebase.*
