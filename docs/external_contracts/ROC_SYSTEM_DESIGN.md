# ROC — Rack of Champions  
## Official Competitive League System Design & Specification

**Document version:** 1.1.0  
**Date:** 2026-08-05  
**Status:** SOURCE OF TRUTH — product + engineering + RealAI  
**Official name:** **ROC — Rack of Champions**  
**Hierarchy:** **RackUp** = platform · **ROC** = competitive league system inside RackUp  
**Related contracts:** `RACKUP_GAME_KNOWLEDGE_AND_AI_CONTRACT.md`, `REALAI_RACKUP_WIRING_CONTRACT.md`  
**Copies:** `docs/ROC_SYSTEM_DESIGN.md` · `C:\Users\tsmit\realai_documents\ROC_SYSTEM_DESIGN.md`

---

## 0. Brand & positioning

| Element | Spec |
|---------|------|
| **Name** | ROC — Rack of Champions |
| **Spoken** | “Rock” or “R-O-C” (product UI: **ROC**) |
| **Positioning** | All-inclusive yet serious. Casual players can join and enjoy it; high-level players respect competition, structure, ratings, and money handling. |
| **Tone** | Clean, confident, professional. No gimmicks, no cartoon economy language. |
| **Money language** | Players Fund · Projected payout · Ledger · Paid out — never “loot,” “coins,” or opaque “prize vault.” |

### 0.1 What ROC is

**ROC** is RackUp’s **official competitive league operating layer**. Anyone (player or hall operator) can create and run a **ROC League** (the operating unit; also called a league chapter in UI copy).

Each ROC League:

- Runs **sessions** (weekly nights, season weeks, or event days).
- Supports **formats** rolled out in fixed order (Singles → … → Teams of 5).
- Plays supported **game styles** (8/9/10-ball, One Pocket, RackUp Pyramid).
- Collects **dues, entries, side pots** on a **public ledger**.
- **Automatically pays** session prize winners at **end of session**.
- Uses the **shared continuous RackUp/ROC rating ladder** (BCA-style / Fargo-like number — not APA skill levels), halls, social, matchmaking hooks, and **RealAI** validation.

### 0.2 Non-negotiables

1. Every dollar is a ledger line — balances are derived, not invented.  
2. Prize money lives on the **Players Fund** in real time — never a black box.  
3. Split percentages are always visible (default **45 / 35 / 20**).  
4. **Projected place payouts** are visible before the session ends.  
5. Full payout history is always available.  
6. Later formats never break earlier ones.  
7. New game styles plug in without rewriting money or session cores.  
8. **Ratings are continuous numbers** (exact value for matchmaking, handicaps, `rating_update`). Display bands are labels only.

### 0.3 Roles

| Role | Code | Responsibilities |
|------|------|------------------|
| **ROC Operator** | `OPERATOR` | Owner: create league, config, seasons, sessions, dues, payouts, roster/teams, full ledger |
| **ROC Admin** | `ADMIN` | Delegated operator tools (optional) |
| **Player** | `PLAYER` | Register, pay, play, view money + projections, receive payouts |
| **Team Captain** | `CAPTAIN` | Teams of 5 (and optional doubles): roster, lineup, team payment coordination |
| **RackUp** | `PLATFORM` | Default 20% platform share, co-host majors, compliance freezes, dispute escalation |

### 0.4 Format rollout order (exact)

| Phase | Code | Display name |
|-------|------|--------------|
| 1 | `SINGLES` | Singles |
| 2 | `SCOTCH_DOUBLES` | Scotch Doubles League |
| 3 | `SCOTCH_JJ` | Scotch Jack & Jill |
| 4 | `TEAMS_5` | Teams of 5 |

Each **Season** locks exactly one format. A ROC League may run multiple seasons (including different formats) in parallel after unlock.

### 0.5 Game styles (day one, expandable)

| Code | Display |
|------|---------|
| `eight_ball` | 8-Ball |
| `nine_ball` | 9-Ball |
| `ten_ball` | 10-Ball |
| `one_pocket` | One Pocket |
| `pyramid` | RackUp Pyramid |

### 0.6 Rating model at a glance (locked)

| Property | Spec |
|----------|------|
| Style | **Continuous** skill number (BCA / FargoRate-like continuum) |
| Not | APA-style broad skill levels as the competitive core |
| Storage | Shared `users.rating` (single ladder for all of RackUp + ROC) |
| Matchmaking / handicaps / updates | **Exact number only** |
| Display bands | Optional labels for readability (see §7) |
| Example display | **Advanced • 547** |

Full rating + cross-league + RealAI rules: **§7**.

---

# 1. Complete data models

All money: **integer cents** (`bigint`). No floating-point currency.

### 1.1 Conceptual ER

```
RocLeague                    ← operating unit (one operator-owned league)
  ├── RocMember
  ├── RocSettings
  ├── LedgerAccount[]        ← Players Fund, Operator, Platform, …
  ├── LedgerEntry[]          ← immutable
  ├── Season
  │     ├── format (locked)
  │     ├── Team[] + TeamMember[]
  │     ├── Entry[] + EntrySplit[]
  │     ├── SeasonStanding[]
  │     └── Session
  │           ├── split_snapshot / payout_structure_snapshot
  │           ├── SessionParticipant[]
  │           ├── RocMatch[]
  │           ├── SidePot[]
  │           ├── Payout[] + PayoutLine[]
  │           └── SessionCloseJob
  └── Payment[]
```

### 1.2 `RocLeague`

| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid PK | |
| `slug` | string unique | e.g. `vegas-strip-roc` |
| `name` | string | Display name |
| `tagline` | string? | Short professional blurb |
| `description` | text? | |
| `status` | `DRAFT` \| `ACTIVE` \| `SUSPENDED` \| `ARCHIVED` | |
| `visibility` | `PUBLIC` \| `UNLISTED` \| `INVITE_ONLY` | |
| `owner_user_id` | uuid | ROC Operator |
| `home_hall_id` | uuid? | Optional home venue |
| `region` | string? | |
| `enabled_formats` | jsonb `string[]` | Grows: `["SINGLES"]` → + doubles… |
| `enabled_game_styles` | jsonb `string[]` | Subset of registry |
| `default_split` | jsonb | bps — see §2 |
| `rules_markdown` | text? | Must-accept rules |
| `rating_policy` | jsonb | floors, convert foreign ratings, etc. |
| `co_host_rackup` | boolean | RackUp co-host flag for big events |
| `branding_json` | jsonb? | Optional logo colors (clean, not gimmicky) |
| `created_at` / `updated_at` | timestamptz | |

> **Naming note:** Internal code/module may use `roc` / `RocLeague`. UI always says **ROC** / **ROC League**. Do not market “Territories” as the product name; ROC is official.

### 1.3 `RocMember`

| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid | |
| `roc_league_id` | uuid | |
| `user_id` | uuid | |
| `role` | `OPERATOR` \| `ADMIN` \| `PLAYER` | |
| `status` | `ACTIVE` \| `BANNED` \| `LEFT` | |
| `joined_at` | timestamptz | |

Unique `(roc_league_id, user_id)`.

### 1.4 `RocSettings`

| Field | Type | Notes |
|-------|------|-------|
| `roc_league_id` | uuid PK/FK | |
| `currency` | `USD` (v1) | |
| `default_dues_cents` | bigint | |
| `default_session_entry_cents` | bigint | |
| `payout_method_policy` | `AUTO_WALLET` \| `AUTO_STRIPE` \| `MARK_PAID_MANUAL` | |
| `require_realai_validate` | boolean default **true** | |
| `allow_money_matches_inside` | boolean | |
| `allow_brackets_inside` | boolean | |
| `dues_to_fund_mode` | `NONE` \| `EQUAL_PER_SESSION` \| `FIRST_SESSION` \| `END_OF_SEASON_ONLY` | Default: `EQUAL_PER_SESSION` |

### 1.5 `Season`

| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid | |
| `roc_league_id` | uuid | |
| `name` | string | e.g. “ROC Fall 2026 Singles” |
| `status` | `DRAFT` \| `REGISTRATION` \| `ACTIVE` \| `COMPLETED` \| `CANCELLED` | |
| `format` | `SINGLES` \| `SCOTCH_DOUBLES` \| `SCOTCH_JJ` \| `TEAMS_5` | **Immutable after first paid entry** |
| `format_config` | jsonb | Format-specific — §1.6 |
| `primary_game_style` | string | Registry code |
| `allowed_game_styles` | jsonb | Optional multi-game season |
| `starts_on` / `ends_on` | date | |
| `schedule_json` | jsonb | Weekly template |
| `dues_cents` | bigint | |
| `session_entry_cents` | bigint | |
| `split_override` | jsonb? | Else league default |
| `payout_structure` | jsonb | Place table — §3 |
| `standings_policy` | jsonb | W/L/forfeit/bye points |
| `max_entries` | int? | |
| `registration_opens_at` / `closes_at` | timestamptz? | |
| `co_host_rackup` | boolean | Event-level co-host |

**Invariant:** One season = one format. Multi-format ROC Leagues run **parallel seasons**.

### 1.6 `format_config` by format

**Singles**
```json
{
  "pairing": "INDIVIDUAL",
  "gender_policy": "OPEN",
  "rating_impact": "INDIVIDUAL",
  "payment_entity": "USER"
}
```

**Scotch Doubles League**
```json
{
  "pairing": "FIXED_PARTNER",
  "scotch_rules": "ALTERNATE_SHOT",
  "partner_change_policy": "LOCKED_AFTER_WEEK_1",
  "rating_impact": "BOTH_PARTNERS",
  "payment_entity": "PARTNERSHIP",
  "default_payout_split": "EQUAL"
}
```

**Scotch Jack & Jill**
```json
{
  "pairing": "MIXED_GENDER",
  "require_gender_declared": true,
  "pair_rule": "ONE_M_ONE_F",
  "scotch_rules": "ALTERNATE_SHOT",
  "rating_impact": "BOTH_PARTNERS",
  "payment_entity": "PARTNERSHIP",
  "default_payout_split": "EQUAL"
}
```

**Teams of 5**
```json
{
  "roster_size": 5,
  "min_active_per_session": 3,
  "max_roster": 7,
  "lineup_deadline_minutes": 30,
  "match_model": "BEST_OF_N_SINGLES",
  "rating_impact": "INDIVIDUAL_MATCHES_PLUS_TEAM_STANDINGS",
  "payment_entity": "TEAM",
  "captain_required": true,
  "default_payout_split": "EQUAL_CHECKED_IN"
}
```

### 1.7 Competitor abstraction (format-safe)

Every money and standings attachment uses:

| Field | Type |
|-------|------|
| `competitor_type` | `USER` \| `TEAM` |
| `competitor_id` | uuid |

| Format | competitor_type | Standings & session payouts |
|--------|-----------------|----------------------------|
| Singles | `USER` | Individual |
| Scotch Doubles | `TEAM` (size 2) | Partnership |
| Scotch JJ | `TEAM` (size 2 + gender rule) | Partnership |
| Teams of 5 | `TEAM` (5–7) | Team |

### 1.8 `Team`

| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid | |
| `season_id` | uuid | |
| `name` | string | |
| `captain_user_id` | uuid | |
| `status` | `FORMING` \| `ACTIVE` \| `WITHDRAWN` | |
| `avatar_url` | text? | |

### 1.9 `TeamMember`

| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid | |
| `team_id` | uuid | |
| `user_id` | uuid | |
| `role` | `CAPTAIN` \| `PLAYER` \| `SUB` | |
| `status` | `ACTIVE` \| `REMOVED` | |
| `jersey_order` | int? | |
| `joined_at` | timestamptz | |

### 1.10 `Entry`

| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid | |
| `season_id` | uuid | |
| `session_id` | uuid? | Session-scoped fees |
| `competitor_type` / `competitor_id` | | Who is entered |
| `entry_kind` | `SEASON_DUES` \| `SESSION_ENTRY` \| `EVENT_ENTRY` \| `SIDE_POT` | |
| `amount_due_cents` | bigint | |
| `amount_paid_cents` | bigint | |
| `status` | `DUE` \| `PARTIAL` \| `PAID` \| `WAIVED` \| `REFUNDED` \| `VOID` | |
| `payer_user_id` | uuid | Who paid |
| `created_at` | timestamptz | |

### 1.11 `EntrySplit` (doubles / teams)

| Field | Type | Notes |
|-------|------|-------|
| `entry_id` | uuid | |
| `user_id` | uuid | |
| `share_cents` | bigint | Contribution toward team/partnership fee |
| `payment_id` | uuid? | |

### 1.12 `Session`

One competitive unit that **closes with automatic payouts**.

| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid | |
| `season_id` | uuid | |
| `roc_league_id` | uuid | Denormalized |
| `name` | string | e.g. “Week 3” |
| `session_index` | int | |
| `status` | `SCHEDULED` \| `REGISTRATION` \| `LIVE` \| `SCORING` \| `PAYING_OUT` \| `CLOSED` \| `CANCELLED` | |
| `scheduled_start` / `scheduled_end` | timestamptz | |
| `opened_at` / `closed_at` | timestamptz? | |
| `game_style` | string | |
| `format` | string | Frozen copy of season format |
| `entry_fee_cents` | bigint | Snapshot |
| `split_snapshot` | jsonb | **Frozen at open** |
| `payout_structure_snapshot` | jsonb | **Frozen at open** |
| `bracket_mode` | `ROUND_ROBIN` \| `LADDER` \| `SINGLE_ELIM` \| `SWISS` \| `CUSTOM` | |
| `auto_payout` | boolean default true | |
| `close_summary_json` | jsonb? | Post-close breakdown |

### 1.13 `SessionParticipant`

| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid | |
| `session_id` | uuid | |
| `competitor_type` / `competitor_id` | | |
| `seed` | int? | |
| `check_in_status` | `EXPECTED` \| `CHECKED_IN` \| `NO_SHOW` | |
| `entry_id` | uuid? | |
| `final_place` | int? | |
| `final_points` | int? | |
| `payout_cents` | bigint default 0 | |
| `payout_status` | `NONE` \| `PROJECTED` \| `PAID` \| `FAILED` \| `FORFEITED` | |

### 1.14 `RocMatch`

| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid | |
| `session_id` | uuid | |
| `season_id` | uuid | |
| `roc_league_id` | uuid | |
| `game_style` | string | |
| `format` | string | |
| `status` | `SCHEDULED` \| `LIVE` \| `PENDING_CONFIRM` \| `COMPLETED` \| `DISPUTED` \| `CANCELLED` | |
| `competitor_a_type` / `competitor_a_id` | | |
| `competitor_b_type` / `competitor_b_id` | | |
| `player_ids_json` | uuid[] | Flattened users for rating |
| `race_to` | int? | |
| `table_size_ft` | int? | Pyramid |
| `skill_level` | string? | Pyramid |
| `a_score` / `b_score` | int? | |
| `winner_competitor_id` | uuid? | |
| `reported_by` | uuid? | |
| `confirmed_by` | uuid[] | Dual confirm |
| `realai_validation_json` | jsonb? | |
| `pool_match_id` | uuid? | Link core match engine |
| `is_money_match` | boolean | Side money match |
| `bracket_node_id` | string? | |
| `played_at` | timestamptz? | |

### 1.15 Ledger

#### `LedgerAccount`

| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid | |
| `roc_league_id` | uuid | |
| `kind` | enum below | |
| `name` | string | |
| `currency` | string | |
| `is_system` | boolean | |

| Kind | Purpose |
|------|---------|
| `PLAYERS_FUND` | Prize pool (default 45% of eligible inflows) |
| `OPERATOR_REVENUE` | ROC Operator share (35%) |
| `PLATFORM_REVENUE` | RackUp share (20%) |
| `HOLDING` | Optional clearing before split |
| `PAYOUT_CLEARING` | Outbound in flight |
| `RESERVE` | Optional rain-out / reserve |
| `SIDE_POT` | Per-side-pot account (`side_pot_id` in metadata) |

**Balance** = Σ credits − Σ debits (cached balance allowed; reconcile to ledger).

#### `LedgerEntry` (immutable — no update/delete)

| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid | |
| `roc_league_id` | uuid | |
| `account_id` | uuid | |
| `direction` | `CREDIT` \| `DEBIT` | |
| `amount_cents` | bigint > 0 | |
| `balance_after_cents` | bigint | Audit snapshot |
| `entry_type` | enum §2.2 | |
| `session_id` / `season_id` | uuid? | |
| `competitor_type` / `competitor_id` | ? | |
| `payer_user_id` / `payee_user_id` | uuid? | |
| `payment_id` / `payout_id` | uuid? | |
| `related_entry_id` | uuid? | Split group / reversal |
| `idempotency_key` | string unique | |
| `memo` | string | Always human-readable & visible |
| `metadata_json` | jsonb | |
| `created_at` | timestamptz | |
| `created_by` | uuid \| `SYSTEM` | |

Corrections = reversing entry + new entry only.

### 1.16 `Payment`

| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid | |
| `roc_league_id` | uuid | |
| `user_id` | uuid | Payer |
| `entry_id` | uuid? | |
| `amount_cents` | bigint | |
| `status` | `PENDING` \| `SUCCEEDED` \| `FAILED` \| `REFUNDED` | |
| `method` | `CARD` \| `WALLET` \| `CASH` \| `COMP` | |
| `provider` | `stripe` \| `mock` \| `manual` | |
| `provider_ref` | string? | |
| `receipt_url` | string? | |
| `created_at` | timestamptz | |

`SUCCEEDED` → atomic ledger post (§2.3).

### 1.17 `Payout` + `PayoutLine`

**Payout**

| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid | |
| `roc_league_id` | uuid | |
| `session_id` | uuid | |
| `place` | int | 1, 2, 3… |
| `competitor_type` / `competitor_id` | | |
| `gross_cents` | bigint | |
| `status` | `PROJECTED` \| `FINALIZED` \| `TRANSFERRING` \| `PAID` \| `FAILED` \| `VOID` | |
| `payee_breakdown_json` | jsonb | Summary |
| `ledger_entry_ids` | uuid[] | |
| `paid_at` | timestamptz? | |
| `failure_reason` | text? | |

**PayoutLine** (team / partnership payees)

| Field | Type | Notes |
|-------|------|-------|
| `payout_id` | uuid | |
| `user_id` | uuid | |
| `amount_cents` | bigint | |
| `basis` | `EQUAL_SPLIT` \| `EQUAL_CHECKED_IN` \| `ENTRY_CONTRIBUTION` \| `CAPTAIN_ALLOC` \| `CUSTOM` | |
| `status` | mirrors payout line status | |

### 1.18 `SidePot`

| Field | Type | Notes |
|-------|------|-------|
| `id` | uuid | |
| `session_id` | uuid | |
| `name` | string | e.g. “Break & Run” |
| `entry_cents` | bigint | |
| `split` | jsonb | May differ from default |
| `payout_structure` | jsonb | |
| `status` | `OPEN` \| `LOCKED` \| `PAID` | |

### 1.19 Standings

**`SeasonStanding`:** season + competitor + played/wins/losses/points + `prize_money_won_cents` + rank.  
**`TeamContribution` (Teams of 5):** user_id, session_id, boards won, points, for transparency not necessarily money.

### 1.20 Ops

| Entity | Purpose |
|--------|---------|
| `RocAuditLog` | Config, manual payouts, voids |
| `SessionCloseJob` | Auto-payout state machine |
| `RocDispute` | Score/money hold before close |

---

# 2. Exact money flow and ledger rules

### 2.1 Default revenue split (configurable)

| Bucket | Default | Account |
|--------|---------|---------|
| **Players Fund** (prize pools) | **45%** | `PLAYERS_FUND` |
| **ROC Operator** | **35%** | `OPERATOR_REVENUE` |
| **RackUp** (platform) | **20%** | `PLATFORM_REVENUE` |

Stored in basis points (must sum to **10000**):

```json
{
  "players_fund_bps": 4500,
  "operator_bps": 3500,
  "platform_bps": 2000
}
```

**Precedence:** League default → Season override → **Session snapshot at open** (immutable for that session).

Co-hosted majors may publish a different split **before registration** (still fully visible).

### 2.2 Ledger entry types

| Type | Direction | Meaning |
|------|-----------|---------|
| `DUES_IN` | CREDIT | Season dues |
| `SESSION_ENTRY_IN` | CREDIT | Nightly entry |
| `EVENT_ENTRY_IN` | CREDIT | Bracket/event fee |
| `SIDE_POT_IN` | CREDIT | Side pot buy-in |
| `SPONSOR_IN` | CREDIT | Sponsor (default 100% to Players Fund unless configured) |
| `ADJUSTMENT_IN` | CREDIT | Audited manual |
| `PAYOUT_OUT` | DEBIT | Prize paid from Players Fund |
| `OPERATOR_WITHDRAWAL` | DEBIT | Operator takes revenue |
| `PLATFORM_SETTLEMENT` | DEBIT | Platform settlement |
| `REFUND_OUT` | DEBIT | Refund (paired reverse group) |
| `TRANSFER` | both | Internal rebalance |

### 2.3 Payment → split post (atomic, idempotent)

On `Payment.status = SUCCEEDED` for amount `A`:

```
group_id = new uuid
pf = floor(A * players_fund_bps / 10000)
op = floor(A * operator_bps / 10000)
pl = A - pf - op   // remainder

DUST POLICY (fixed): remainder cents go to PLAYERS_FUND
  → reassign: pl' = floor(A * platform_bps / 10000)
              pf' = A - op - pl'   // players fund absorbs remainder

CREDIT PLAYERS_FUND   pf'   memo: "Session entry split — Players Fund 45%"
CREDIT OPERATOR       op    memo: "Session entry split — ROC Operator 35%"
CREDIT PLATFORM       pl'   memo: "Session entry split — RackUp 20%"
```

All three share `related_entry_id = group_id` and `idempotency_key` derived from `payment_id`.

**Player pay confirmation UI must show the dollar split before charge.**

### 2.4 Visibility (always on)

| Audience | Sees |
|----------|------|
| Any league member | Total paid in (by category), split %, Players Fund balance, projected places, full payout history, full ledger (payer names may be display-name level) |
| Public league page | Summary totals + fund + structure; mask sensitive PII |
| Operator | + dues aging, failed payouts, operator/platform balances |
| RackUp admin | Everything + freeze |

### 2.5 Hard bans

- No UPDATE/DELETE of ledger rows  
- No mid-session split change after open  
- No paying prizes from Operator account without explicit audited transfer  
- No hiding platform fee  
- Players Fund never negative  

### 2.6 Individual vs team money

| | Singles | Doubles / JJ | Teams of 5 |
|--|---------|--------------|------------|
| Entry competitor | USER | TEAM | TEAM |
| Who can pay | Player | Either partner (tracked in EntrySplit) | Captain or members (EntrySplit) |
| Session payout payee | USER | TEAM → PayoutLines | TEAM → PayoutLines |
| Default line split | 100% | 50/50 | Equal among checked-in active roster that session |

### 2.7 Money matches & brackets inside ROC

- **Money match:** optional escrow via existing money-match module; separate from session Players Fund unless both opt into a **side pot**.  
- **Brackets:** larger single-elim/swiss events as sessions with `bracket_mode`; same ledger + auto-payout on close.  
- **RackUp co-host:** flagged season/session; published fee split; still one transparent ledger under the ROC League.

### 2.8 Session Players Fund slice

```
session_inflows = ledger credits tagged session_id
                  of types SESSION_ENTRY_IN (+ allocated DUES share, SPONSOR tagged, …)
session_players_fund = sum of PLAYERS_FUND credits for those inflows
                      − refunds/reversals for session
```

Season dues allocation follows `dues_to_fund_mode` (default equal across planned sessions).

---

# 3. Projected and final payouts

### 3.1 Payout structure

**Percent of session Players Fund:**
```json
{
  "mode": "PERCENT_OF_FUND",
  "places": [
    { "place": 1, "bps": 5000 },
    { "place": 2, "bps": 3000 },
    { "place": 3, "bps": 2000 }
  ]
}
```

**Fixed cents:**
```json
{
  "mode": "FIXED_CENTS",
  "places": [
    { "place": 1, "amount_cents": 15000 },
    { "place": 2, "amount_cents": 8000 }
  ],
  "shortfall_policy": "SCALE"
}
```

`shortfall_policy`: `SCALE` (pro-rate) or `HOLD` (operator alert, no auto-pay).

### 3.2 Live projected payouts

```
GET /roc/leagues/:id/sessions/:sid/projections
```

1. Load frozen `split_snapshot` + `payout_structure_snapshot`.  
2. `fund = session_players_fund` from ledger.  
3. Current standings / bracket → provisional places.  
4. `projected_cents` per place.  
5. Map place → competitor; expand team → user lines.  
6. Return table + fund + as-of time + unpaid entry warnings.

**Always show place $ even if competitor is TBD.**

### 3.3 Final payouts

On session close: recompute final places → final fund → create `Payout` `FINALIZED` → execute (§4) → history immutable for that session.

---

# 4. End-of-session automatic payout flow

### 4.1 Session status machine

```
SCHEDULED → REGISTRATION → LIVE → SCORING → PAYING_OUT → CLOSED
                         ↘ CANCELLED (refund path)
```

### 4.2 Triggers

- Operator: **End session & pay out**  
- System: all matches terminal + grace period  
- System: scheduled end + scores complete  

### 4.3 `SessionCloseJob` (idempotent)

```
1. Lock session (LIVE/SCORING → PAYING_OUT)
2. Block if DISPUTED matches (unless operator force + audit)
3. Final standings → final_place on participants
4. fund = session Players Fund slice
5. Build Payout[] (idempotency_key: session_id:place:competitor_id)
6. For each payout:
     expand PayoutLines
     DEBIT PLAYERS_FUND / CREDIT PAYOUT_CLEARING
     transfer (wallet/stripe/manual mark)
     success → PAID; failure → FAILED + alert (funds safe)
7. Notify winners
8. CLOSED + close_summary_json
9. WS: roc:session_closed
10. Optional non-blocking RealAI coach hooks
```

### 4.4 Operator controls

| Control | Effect |
|---------|--------|
| Pause auto-payout | Standings close; money stays in Fund |
| Adjust place | Only before PAYING_OUT; audited |
| Mark paid external | Same ledger debit + receipt |
| Cancel session | Refund policy via reverse ledger groups |

---

# 5. User flows (format rollout order)

### 5.1 Phase 1 — Singles

**Operator:** Create ROC League → enable Singles + games → set split (or 45/35/20) → Season → Sessions → collect entries → matches → scores → End & pay out.  

**Player:** Join → accept rules → pay (see split) → check in → play → confirm score → watch projections → receive payout.  

**Rating:** per match, each player’s **continuous** rating via `rating_update`; UI shows e.g. Advanced • 547.

### 5.2 Phase 2 — Scotch Doubles League

- Season format `SCOTCH_DOUBLES`.  
- Form Team of 2; entry on partnership + EntrySplit.  
- Standings/payouts on TEAM; default 50/50 lines.  
- Both partners in `player_ids_json` for ratings.  
- **No change** to existing Singles seasons.

### 5.3 Phase 3 — Scotch Jack & Jill

- Same partnership model + **mixed-gender pair rule**.  
- Registration rejects illegal pairs.  
- Money/standings identical to doubles competitor model.

### 5.4 Phase 4 — Teams of 5

- Roster 5–7; captain required; session lineup minimum.  
- Team entry + optional individual dues.  
- Team standings; board-level individual ratings.  
- Payout to team → lines (default equal checked-in).  
- Contribution stats for transparency.

---

# 6. Operator dashboard requirements

### 6.1 IA

```
ROC League Home
  Overview          — live session, fund, members
  Ledger            — full transparency + CSV export
  Seasons
  Sessions          — live board
  Players / Teams
  Payments & Dues
  Payouts
  Settings          — split, formats, games, rules
  Audit log
```

### 6.2 Live session board (primary)

**Sticky money bar (always visible):**

`Players Fund $X  ·  Operator $Y  ·  RackUp $Z  ·  Split 45/35/20  ·  Session in $W`

| Panel | Content |
|-------|---------|
| Projected payouts | Place · competitor · $ |
| Standings | W-L-Pts |
| Matches | Live scores, confirm, RealAI valid flag |
| Dues/entries | Paid / due / partial |
| Actions | Open, pair, end & pay out, pause, dispute |

### 6.3 Ledger UX

- Filter by account, session, user, type  
- Drill-down: “Where did my $20 go?” → payment → 3-way split  
- Export night summary PDF/CSV  

### 6.4 Player money surface

Same fund + projections (read-only); my payments; my payouts; my team splits. Platform fee never hidden.

### 6.5 Notifications

Payment received · session open · confirm score · payout sent · dues overdue · failed payout (operator).

---

# 7. Ratings model (BCA-style continuous — locked)

## 7.1 Core principle

ROC uses a **continuous rating number** in the same family as **BCA / FargoRate** skill continua — **not** APA-style coarse skill levels as the competitive identity.

| Rule | Detail |
|------|--------|
| **Single source of truth** | Shared **RackUp ladder** (`users.rating`). ROC does **not** maintain a second competitive Elo. |
| **What it is** | One continuous number that moves after rated matches via RealAI `rating_update`. |
| **What it is not** | A fixed “SL 4 / SL 5” bucket as the stored rating. APA SL may be **imported and converted**, then discarded as competitive truth. |
| **Precision** | Integer (or one decimal if product later allows; v1 = **integer**). Matchmaking and handicaps use the **exact** value. |
| **Owner of math** | **RealAI** computes `rating_after`. RackUp **persists** only. |

Typical scale orientation (descriptive, not hard caps for math): many recreational/league players will cluster roughly mid-scale; elites sit higher. Exact K/algorithm is RealAI `elo_logistic_v1` (or successor named in `result.algorithm`).

### 7.1.1 Player rating fields (storage)

| Field | Owner | Notes |
|-------|-------|-------|
| `users.rating` | RackUp DB | Continuous ROC/RackUp rating — **competitive truth** |
| `users.rating_updated_at` | RackUp DB | Optional; set on successful `rating_update` |
| `users.last_match_delta` | RackUp DB | Optional audit |
| External APA/BCA/TAP/VNEA | Import / profile | **Display + conversion only**; never overwrite ladder blindly after ROC history exists |

### 7.1.2 Optional display bands (labels only)

Bands exist **only for readability** in UI, standings chips, and social cards.  
They **must not** drive matchmaking windows, handicaps, or `rating_update` inputs.

| Rating range | Band label |
|--------------|------------|
| Under 400 | **Novice** |
| 400–499 | **Intermediate** |
| 500–599 | **Advanced** |
| 600–699 | **Expert** |
| 700+ | **Elite** |

**Canonical display format:**

```text
{Band} • {exact_rating}
```

**Examples:**

| Rating | Display |
|--------|---------|
| 312 | Novice • 312 |
| 450 | Intermediate • 450 |
| **547** | **Advanced • 547** |
| 640 | Expert • 640 |
| 720 | Elite • 720 |

**Band helper (spec):**

```
function displayBand(r: number): string {
  if (r < 400) return 'Novice';
  if (r < 500) return 'Intermediate';
  if (r < 600) return 'Advanced';
  if (r < 700) return 'Expert';
  return 'Elite';
}
// UI: `${displayBand(rating)} • ${rating}`
```

### 7.1.3 What uses the exact number vs the band

| Use case | Exact continuous rating | Band label |
|----------|-------------------------|------------|
| Matchmaking fit / window | **Yes** | No |
| Handicap suggestions | **Yes** | No |
| RealAI `rating_update` | **Yes** (before/after) | Optional echo only |
| Season seeding by skill | **Yes** (unless operator chooses pure random) | No |
| Profile / standings chip | Yes (number) | **Yes** (label) |
| Marketing copy | Optional | Optional |

### 7.1.4 Format-specific rating impact

| Format | Who receives `rating_update` |
|--------|------------------------------|
| Singles | Both individual players |
| Scotch Doubles / JJ | **Both partners** (each user in `player_ids_json`) |
| Teams of 5 | Each user on a **board match** they played; team standings are separate from rating |

Default: full participation weight per individual match outcome unless season `rating_policy` sets an explicit `rating_weight` (e.g. Pyramid skill matrix 0.7–1.15).

### 7.1.5 New players & provisional

- Default seed if no history and no convertible external rating: product default (e.g. **500**) — **Intermediate • 500**.  
- If only external league rating exists → run **`rating_convert`** (§7.2) → optional one-time seed of `users.rating` when `matches_played_rackup == 0`.  
- After ROC/RackUp match history exists, **only** `rating_update` moves the ladder.

---

## 7.2 Cross-league conversion (BCA / Fargo · APA · TAP · VNEA)

RealAI (and RackUp’s rating layer invoking it) **must** accept external ratings and produce an **estimated continuous ROC rating + confidence**.

### 7.2.1 Systems supported

| System | Typical form | Notes |
|--------|--------------|-------|
| **BCA / FargoRate** | Continuous skill number | Closest native shape to ROC; often near pass-through after scale normalize |
| **APA** | Skill levels ~2–7 (sometimes 1–9) | Coarse bands → convert to continuum estimate |
| **TAP** | Skill steps or charter points | Higher = stronger; scale via `tap_scale` when known |
| **VNEA** | Division / skill tier or numeric | Map tiers → continuum centers |

### 7.2.2 Preference when multiple sources exist

1. `primary_rating_system` if set by player/operator.  
2. Else **most recent** with `trusted: true`.  
3. Else priority: **FargoRate/BCA continuous** → **APA SL** → **TAP** → **VNEA**.  
4. Once player has sufficient ROC match history (`matches_played_rackup ≥ 5` suggested), **ignore external for competitive truth**; still show badges.

### 7.2.3 Approximate mapping ranges (v1 heuristics — refinable with live data)

These are **estimates for onboarding and mixed matchmaking**, not official APA/BCA handicaps.

#### APA skill level → continuous ROC rating (band centers)

| APA SL | ≈ ROC continuous | Display band (label only) |
|--------|------------------|---------------------------|
| 2 | ~320 | Novice |
| 3 | ~420 | Intermediate |
| 4 | ~520 | Advanced |
| 5 | ~600 | Expert |
| 6 | ~680 | Expert |
| 7 | ~760 | Elite |
| 8+ | ~820+ | Elite |

Smooth formula option: map SL 2→320 … SL 7→760 linearly, then clamp.  
**Note:** This table is aligned to the **locked ROC display bands** (400 / 500 / 600 / 700 cuts). Refine with empirical data; keep ability shapes stable.

#### BCA / FargoRate → ROC

| Input | Conversion (v1) |
|-------|-----------------|
| FargoRate / BCA continuum already in ~200–800 | **Prefer pass-through** (clamp to product min/max if any) |
| Host provides `scale: fargo` | `roc ≈ round(fargo)` |
| Host provides alternate scale | Require `from_scale` metadata; do not guess silently |

#### TAP → ROC (v1)

| If TAP looks like | Convert |
|-------------------|---------|
| 1–9 skill steps | Same centers as APA table |
| Charter points 20–100 | Map mid-pack ~500; document charter in `tap_scale` |
| Unknown | Return low `confidence` + wide interval |

#### VNEA → ROC (v1)

| VNEA tier (illustrative) | ≈ ROC |
|--------------------------|-------|
| Lower division | ~380–450 |
| Mid | ~500–580 |
| Upper | ~620–700 |
| Open / top | ~720+ |

Numeric 1–7: use APA-like centers.

### 7.2.4 Ability: `rating_convert`

**Request (envelope):**
```json
{
  "ability": "rating_convert",
  "player": {
    "player_id": "u1",
    "rating": 500,
    "rating_system": "rackup",
    "matches_played_rackup": 0,
    "league_ratings": {
      "apa": 4,
      "bca": null,
      "fargo": null,
      "tap": null,
      "vnea": null
    },
    "primary_rating_system": "apa"
  },
  "payload": {
    "from_system": "apa",
    "from_value": 4,
    "from_scale": "skill_1_9",
    "also_known": [],
    "want": ["rackup", "bca", "fargo", "tap", "vnea"]
  }
}
```

**Result:**
```json
{
  "rackup_rating_estimate": 520,
  "band_label": "Advanced",
  "confidence": 0.68,
  "equivalents": {
    "apa": { "value": 4, "display": "SL 4" },
    "fargo": { "value": 520, "display": "~520" },
    "bca": { "value": 520, "display": "~520 continuum" },
    "tap": { "value": 4, "display": "skill ~4" },
    "vnea": { "value": "mid", "display": "mid division" }
  },
  "method": "table_v1",
  "notes": "Estimate only; refinable with live ROC data. Bands are labels only."
}
```

### 7.2.5 Mixed-league matchmaking inside ROC

Candidates may have only APA or only Fargo. RealAI `matchmaking`:

1. Convert each candidate to **continuous ROC estimate** when `rating` missing.  
2. Rank on **exact continuous numbers** (estimated or real).  
3. Return `rackup_equivalent_used` + `confidence` per candidate.  
4. Never refuse solely because systems differ.

---

## 7.3 RealAI wiring inside ROC (confirmed)

Canonical transport: `POST {REALAI_BASE_URL}/v1/plugins/rackup-coach`  
(See wiring + game knowledge contracts for full envelopes.)

### 7.3.1 Match finalize path (mandatory order)

```
1. Score report + dual confirm (or operator override)
2. RealAI ability: league_validate
     - Input: game/discipline, scores, table_size, skill_level (Pyramid),
              format context, match_id, pocket logs if any
     - If valid === false → STOP; no standings write; no rating write
3. Persist RocMatch COMPLETED + session standings side effects
4. For each individual player in player_ids_json:
     RealAI ability: rating_update
       - player.rating = continuous rating before match
       - payload: opponent_rating, won, game, scores, rating_weight, …
     RackUp writes rating_after → users.rating
5. Refresh live payout projections (money path independent of rating)
6. Optional: coach / practice_plan (non-blocking)
```

**Never** reverse steps 2–4. **Never** recompute Elo in Nest for production ROC matches.

### 7.3.2 Ability map in ROC context

| Ability | When inside ROC | Respects |
|---------|-----------------|----------|
| `league_validate` | Before persist of session match | `game_style`, Pyramid matrix, format rules where relevant |
| `rating_update` | After persist, per player | Exact continuous rating; format weights; game style |
| `rating_convert` | Registration, import, mixed MM | APA/BCA/Fargo/TAP/VNEA → continuum |
| `matchmaking` | Open challenges / soft pairing assist | Exact ratings; game style; optional format prefs |
| `moderation` | ROC league/session chat, match chat | Channel = roc / session ids |
| `coach` / `pyramid` | Post-match, practice, operator tips | Game style + format (scotch, teams boards) |
| `shot_of_the_day` | Player home / ROC feed (optional) | Discipline from preferred game style; weaknesses |
| `pyramid_rules` | Pyramid sessions / HUD | Locked matrix |
| `video_analysis` | Optional training from ROC context | Game style |
| `hall_context` | Session at home hall | Hall + table speed |

### 7.3.3 Context RackUp must pass on ROC calls

Always include when available:

- `player_id`, `display_name`, **continuous `rating`**, `rating_system: "rackup"`  
- `discipline` / game style (`eight_ball`, `nine_ball`, `ten_ball`, `one_pocket`, `pyramid`)  
- ROC `format` (`SINGLES` \| `SCOTCH_DOUBLES` \| `SCOTCH_JJ` \| `TEAMS_5`)  
- `session_id`, `season_id`, `roc_league_id` (in payload metadata)  
- Pyramid: `table_size`, `skill_level`, scores  
- `league_ratings` + `primary_rating_system` for convert/MM  
- Chat: text + channel + prior_flags for moderation  

### 7.3.4 Coaching, moderation, SOTD, matchmaking — ROC session rules

| Feature | Rule |
|---------|------|
| **Coach** | Session-aware: cite game style + format (e.g. scotch alternate-shot patterns vs singles patterns). Pyramid uses `pyramid` ability / matrix. |
| **Moderation** | All ROC chat paths run `moderation` before fan-out; actions `allow`…`block_and_escalate` unchanged. |
| **SOTD** | Optional personalization using player’s primary ROC game style + continuous rating band for copy only; variety via `shown_shot_ids`. |
| **Matchmaking signals** | Rank on **exact** continuous ratings; soft prefer same game style; format only as soft constraint (e.g. looking for doubles partner). Friends/hall check-ins do not change prize math. |

### 7.3.5 Scorekeeping domain

Domain string for processReport: **`roc_session`**.

---

# 8. Sequential format rollout (no breakage)

### 8.1 Allowlists

```text
Deploy flag: ROC_FORMATS_ENABLED = [SINGLES]  → add SCOTCH_DOUBLES → SCOTCH_JJ → TEAMS_5
League flag: enabled_formats ⊆ deploy allowlist
```

### 8.2 Strategy registry

```
RocFormatStrategy:
  validateRoster()
  createEntry()
  pairMatches()
  applyResult()
  expandPayoutPayees()
  ratingSubjects(match)
```

| Format | Strategy |
|--------|----------|
| SINGLES | `SinglesStrategy` |
| SCOTCH_DOUBLES | `ScotchDoublesStrategy` |
| SCOTCH_JJ | `ScotchJjStrategy` |
| TEAMS_5 | `Teams5Strategy` |

New format = new strategy + enum value. **No edits required to Singles strategy.**

### 8.3 Schema discipline

- `format` column: additive enum/string only  
- Seasons immutable format after first paid entry  
- Unknown format on old client → graceful message, not crash  

---

# 9. Adding game styles later

### 9.1 Registry (single extension point)

```ts
{
  code: 'bank_pool',
  displayName: 'Bank Pool',
  realAiDiscipline: 'bank_pool',
  defaultRaceTo: 8,
  supportsPyramidMatrix: false
}
```

### 9.2 Steps

1. Registry entry + RealAI knowledge for discipline.  
2. UI options from registry (no hard-coded five-way money switches).  
3. Score rules via RealAI / GameRules plugin.  
4. Operators opt in via `enabled_game_styles`.  

**Ledger, sessions, formats, payouts remain game-agnostic.**

---

# 10. API sketch (v1)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/roc/leagues` | Create ROC League |
| GET | `/roc/leagues/:id` | Detail + money summary |
| GET | `/roc/leagues/:id/ledger` | Entries |
| GET | `/roc/leagues/:id/ledger/summary` | Totals, split, fund |
| POST | `/roc/leagues/:id/seasons` | Create season |
| POST | `/roc/seasons/:id/entries` | Register + pay |
| POST | `/roc/seasons/:id/sessions` | Create session |
| POST | `/roc/sessions/:id/open` | Freeze snapshots, open reg |
| POST | `/roc/sessions/:id/matches/:mid/report` | Score + RealAI |
| GET | `/roc/sessions/:id/projections` | Live projected payouts |
| POST | `/roc/sessions/:id/close` | Auto-payout |
| GET | `/roc/sessions/:id/payouts` | History |
| POST | `/roc/seasons/:id/teams` | Team create (fmt 2–4) |
| WS | `roc:league:{id}` | Live fund, scores, projections |

Scorekeeping domain: **`roc_session`**.

---

# 11. Integrity invariants (must test)

1. Successful payment credits sum to payment amount.  
2. Split bps sum to 10000 at session open.  
3. Players Fund ≥ 0 always.  
4. Session payouts ≤ session Players Fund slice (per shortfall policy).  
5. No ledger mutation/delete in app code.  
6. Close/payout job idempotent.  
7. Team PayoutLines sum to team payout.  
8. Closed session final payouts match last projection under same fund (barring late voids).  
9. Enabling TEAMS_5 does not alter Singles seasons.  
10. RealAI-invalid scores never update standings or ratings.  
11. Matchmaking and handicaps never use band labels alone — only continuous rating.  
12. `rating_update` writes `rating_after` to shared ladder; Nest does not recompute competitive Elo in production.  
13. Finalize order always `league_validate` → persist → `rating_update` per player.

---

# 12. Engineering build sequence

| Phase | Deliverable |
|-------|-------------|
| **R0** | RocLeague, members, settings, ledger accounts, payment→split |
| **R1** | Season + Session + Singles matches + projections + auto-payout |
| **R2** | Operator dashboard + player money UI + exports |
| **R3** | Scotch Doubles |
| **R4** | Scotch Jack & Jill |
| **R5** | Teams of 5 + contributions |
| **R6** | Side pots, brackets, money matches, RackUp co-host |

---

# 13. Product summary

**ROC — Rack of Champions** is RackUp’s official competitive league system: operator-run leagues with session-based play, multi-format growth (Singles → Scotch Doubles → Jack & Jill → Teams of 5), multi-game support, RealAI-validated scoring on a **shared continuous BCA/Fargo-like rating ladder** (display e.g. **Advanced • 547**), cross-league conversion from APA/BCA/Fargo/TAP/VNEA, and a **bulletproof transparent ledger** with default **45% Players Fund / 35% ROC Operator / 20% RackUp**, live **projected payouts**, and **automatic end-of-session prize distribution**. Casual players can join; serious players get structure, exact ratings, and total money clarity.

---

## Appendix A — Pay confirm copy (canonical)

> **Session entry: $20.00**  
> Players Fund (45%): **$9.00**  
> ROC Operator (35%): **$7.00**  
> RackUp (20%): **$4.00**  
> These amounts post to the ROC ledger immediately. Prize payouts come only from the Players Fund.

## Appendix B — Relationship to prior “Territories” draft

Any earlier internal draft named “Territories” describes the same operating layer. **Official product name is ROC — Rack of Champions.** Engineering modules, routes, and UI should use **ROC / RocLeague** naming going forward.

## Appendix C — Rating display chip (canonical)

```text
Advanced • 547
```

Band from table in §7.1.2; number is always the full continuous rating. Never show band without number in competitive contexts.

## Appendix D — Changelog

### v1.1.0 — 2026-08-05 (rating model explicit + RealAI harden)

| Added / hardened | Detail |
|------------------|--------|
| **§0.6** | Rating model at a glance (continuous, locked) |
| **§7.1** | Full BCA-style continuous ladder; not APA SL as core |
| **Display bands** | Under 400 Novice · 400–499 Intermediate · 500–599 Advanced · 600–699 Expert · 700+ Elite |
| **Display format** | `{Band} • {rating}` e.g. Advanced • 547 |
| **Exact vs band** | Matchmaking, handicaps, `rating_update` use exact number only |
| **§7.2** | Cross-league conversion BCA/Fargo, APA, TAP, VNEA + confidence + preference order |
| **`rating_convert`** | Request/response shapes for ROC |
| **§7.3** | RealAI match finalize: `league_validate` → persist → `rating_update` (write `rating_after`) |
| **Ability map** | Coach, moderation, SOTD, matchmaking inside ROC respect game style + format |
| **Invariants 11–13** | Continuous rating + finalize order tests |
| **Copies** | `docs/` + `realai_documents/` for RealAI consumption |

### v1.0.0 — 2026-08-05

Initial ROC design: brand, formats, ledger 45/35/20, session auto-payouts, game registry, sequential rollout, operator dashboard, models.

---

*Paths:*  
- `docs/ROC_SYSTEM_DESIGN.md`  
- `C:\Users\tsmit\realai_documents\ROC_SYSTEM_DESIGN.md`  

*Aligns with: continuous shared ratings, RealAI contracts, money escrow patterns, scorekeeping V2, halls/social.*  
*Do not start R0/R1 until this contract is accepted as final for ratings + money.*
