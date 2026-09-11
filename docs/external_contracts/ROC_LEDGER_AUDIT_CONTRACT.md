# ROC Ledger Audit Contract (RealAI read-only)

**Document version:** 1.0.0  
**Date:** 2026-08-05  
**Plugin:** `rackup-coach` **v1.6.0**  
**Module:** `plugins/rackup_coach/money_audit.py`  
**Status:** LOCKED ownership — audit only  

---

## 0. Ownership (non-negotiable)

| System | Owns | Does **not** |
|--------|------|----------------|
| **RackUp** | Stripe, USD ledger, splits, payouts, profile balances, auto-payout jobs | Inventing audit findings |
| **RealAI** | Read-only analysis of **snapshots** RackUp sends | Move money, call Stripe, authorize payouts, invent balances |

```
authorize_payout: always false
owns_ledger: always false
read_only: always true
```

**Gate:** RackUp **must** call `ledger_audit` (and ideally `payout_sanity`) **before** auto-payout release — soft warn on warnings, hard stop on blockers (product policy).

Separate from Glicko-2 `rating_update`.

---

## 1. Abilities

| Ability | Purpose |
|---------|---------|
| `ledger_audit` | Session/season ledger + payout lines + standings consistency |
| `payout_sanity` | Standings rank vs payout lines; format mistakes; fix list |
| `money_anomaly` | Player/operator payment history risk score |

Transport: `POST {REALAI_BASE_URL}/v1/plugins/rackup-coach`  
Envelope: `{ "ability", "player"?, "payload"? }` — **top-level fields are merged into payload**.

---

## 2. Response schema (common)

All three return:

```json
{
  "ok": true,
  "ability": "ledger_audit",
  "status": "pass",
  "owns_ledger": false,
  "owns_payouts": false,
  "authorize_payout": false,
  "read_only": true,
  "provider": "realai",
  "plugin": "rackup-coach",
  "meta": { "roc_league_id": "...", "session_id": "...", "format": "SINGLES" },
  "summary": {
    "ok": true,
    "warning_count": 0,
    "blocker_count": 0,
    "finding_count": 1
  },
  "warnings": [],
  "blockers": [],
  "findings": [
    {
      "severity": "info|warning|blocker",
      "code": "string",
      "message": "plain language",
      "details": {}
    }
  ],
  "plain_language": ["..."],
  "gate": {
    "recommend_before_auto_payout": true,
    "hard_block_if_blockers": true,
    "authorize_payout": false,
    "note": "..."
  },
  "boundary": {
    "realai": "audit analysis only",
    "rackup": "Stripe, ledger writes, split execution, payout release",
    "never": ["authorize_payout", "call_stripe", "invent_balances", "move_money"]
  }
}
```

**Severity**

| Level | Meaning for RackUp |
|-------|--------------------|
| `info` | FYI |
| `warning` | Soft gate — operator can override with acknowledgment |
| `blocker` | Hard gate — do not auto-release payouts |

Amounts are **integer cents** in analysis fields (`*_cents`).

---

## 3. `ledger_audit`

### Input

```json
{
  "ability": "ledger_audit",
  "roc_league_id": "roc_vegas",
  "session_id": "ses_week3",
  "season_id": "sea_fall",
  "format": "SINGLES",
  "configured_split": {
    "players_fund": 0.45,
    "operator": 0.35,
    "rackup": 0.20
  },
  "eligible_inflow_cents": 100000,
  "ledger_entries": [
    {
      "id": "le1",
      "direction": "CREDIT",
      "entry_type": "SESSION_ENTRY",
      "amount_cents": 10000,
      "idempotency_key": "entry_u1_ses",
      "payment_id": "pay_1",
      "competitor_type": "USER",
      "competitor_id": "u1"
    }
  ],
  "payments": [
    { "id": "pay_1", "status": "SUCCEEDED", "amount_cents": 10000 }
  ],
  "payout_lines": [
    {
      "competitor_type": "USER",
      "competitor_id": "u1",
      "place": 1,
      "payout_cents": 25000,
      "payout_status": "PROJECTED"
    }
  ],
  "standings": [
    { "player_id": "u1", "competitor_type": "USER", "final_place": 1 }
  ]
}
```

Split also accepts bps (`4500/3500/2000`) or percents (`45/35/20`).

### Extra output fields

- `split_check` — expected vs observed players fund / operator / rackup  
- `totals` — inflow, payout_lines, held fees  
- `payee_payouts_cents`  
- `by_entry_type_cents`  
- `gate.hard_block_if_blockers`

### Checks

1. Split math (default **45/35/20** or configured)  
2. Sum(payments in) vs sum(payout lines + held fees)  
3. Duplicate idempotency keys / payment ids  
4. Multiple payout lines per competitor  
5. Paid competitors not in standings / missing 1st place payout  
6. Format competitor_type (Singles → USER; doubles/teams → TEAM path)

---

## 4. `payout_sanity`

### Input

```json
{
  "ability": "payout_sanity",
  "format": "SINGLES",
  "session_id": "ses_week3",
  "players_fund_cents": 45000,
  "payout_structure": { "places": { "1": 25000, "2": 15000, "3": 5000 } },
  "standings": [
    { "player_id": "u1", "final_place": 1 },
    { "player_id": "u2", "final_place": 2 }
  ],
  "payout_lines": [
    { "player_id": "u1", "place": 1, "payout_cents": 25000 },
    { "player_id": "u2", "place": 2, "payout_cents": 15000 }
  ]
}
```

### Extra output fields

- `confidence` (0–1)  
- `ranks_match_standings`  
- `total_payout_lines_cents`  
- `line_checks[]`  
- `fix_before_release[]` — actionable line items  
- `gate.release_safe` — true only if ok and confidence ≥ 0.8  

### Checks

- Payout place vs standings place  
- Amount vs payout_structure  
- Missing place lines  
- Payee not in standings  
- Team vs singles `competitor_type` mistakes  

---

## 5. `money_anomaly`

### Input

```json
{
  "ability": "money_anomaly",
  "subject_id": "u9",
  "role": "PLAYER",
  "window_days": 30,
  "payment_history": [
    {
      "id": "p1",
      "status": "SUCCEEDED",
      "amount_cents": 5000,
      "provider_ref": "ch_xxx",
      "type": "PAYMENT"
    }
  ]
}
```

`role`: `PLAYER` | `OPERATOR` | `ADMIN`

### Extra output fields

- `risk_score` 0–100  
- `risk_level`: `none` | `low` | `elevated` | `high` | `critical`  
- `recommended_human_review`  
- `anomalies[]`  
- `counts`  

### Signals

- Refund loops  
- Repeated failed pays then success spikes  
- Missing tx / provider refs on successes  
- Operator withdraw frequency / spike  
- Duplicate payment ids  
- High velocity (info)

---

## 6. Example: pass audit

**Request:** balanced session, 10×$100 entries, 45% prize lines match places 1–3, standings aligned.

**Response (abridged):**

```json
{
  "ok": true,
  "status": "pass",
  "authorize_payout": false,
  "summary": { "ok": true, "warning_count": 0, "blocker_count": 0 },
  "split_check": {
    "configured": { "players_fund": 0.45, "operator": 0.35, "rackup": 0.20 },
    "eligible_inflow_cents": 100000,
    "expected": {
      "players_fund_cents": 45000,
      "operator_cents": 35000,
      "rackup_cents": 20000
    }
  },
  "totals": {
    "inflow_cents": 100000,
    "payout_lines_cents": 45000
  },
  "plain_language": [
    "Inflows approximately balance payout lines + held fees.",
    "Ledger snapshot looks consistent — no blockers found."
  ],
  "gate": {
    "recommend_before_auto_payout": true,
    "hard_block_if_blockers": true,
    "authorize_payout": false
  }
}
```

RackUp may proceed with auto-payout **only under its own policy** after pass.

---

## 7. Example: fail audit

**Request:** single payout line to `ghost` for 80000¢ (not in standings; wrong players-fund size).

**Response (abridged):**

```json
{
  "ok": false,
  "status": "fail",
  "authorize_payout": false,
  "summary": { "ok": false, "blocker_count": 2 },
  "blockers": [
    {
      "severity": "blocker",
      "code": "split_players_fund_mismatch",
      "message": "Payout lines total 80000¢ vs expected players fund 45000¢ (split 45%).",
      "details": { "diff_cents": 35000 }
    },
    {
      "severity": "blocker",
      "code": "paid_not_in_standings",
      "message": "Payout recipients not found in standings.",
      "details": { "competitors": ["USER:ghost"] }
    }
  ],
  "plain_language": [
    "BLOCKER: Payout lines total 80000¢ vs expected players fund 45000¢ (split 45%).",
    "BLOCKER: Payout recipients not found in standings."
  ],
  "gate": {
    "hard_block_if_blockers": true,
    "authorize_payout": false,
    "note": "RackUp must call ledger_audit before auto-payout release. RealAI never authorizes money movement."
  }
}
```

---

## 8. Host integration checklist

1. Before session auto-payout job:  
   - Build ledger snapshot (entries + payments + projected/final payout lines + standings + split snapshot).  
   - `ledger_audit` → if `blocker_count > 0`, **do not** release (hard gate recommended).  
   - `payout_sanity` → apply `fix_before_release` or block.  
2. Optional continuous monitoring: `money_anomaly` on operator withdraw windows.  
3. Show `plain_language` + findings in operator dashboard.  
4. Never treat RealAI `ok: true` as a payment instruction — only as audit clearance.  
5. Glicko-2 `rating_update` remains independent of money audit.

---

## 9. Formats

| Format | Competitor on money lines |
|--------|---------------------------|
| `SINGLES` | `USER` (day-one focus) |
| `SCOTCH_DOUBLES` / `SCOTCH_JJ` | `TEAM` (partnership) — extension path |
| `TEAMS_5` | `TEAM` — extension path |

---

## 10. Files

```
plugins/rackup_coach/money_audit.py
plugins/rackup_coach/abilities/ledger_audit.py
plugins/rackup_coach/abilities/payout_sanity.py
plugins/rackup_coach/abilities/money_anomaly.py
tests/test_money_audit.py
C:\Users\tsmit\realai_documents\ROC_LEDGER_AUDIT_CONTRACT.md
```

---

*RealAI never moves money. RackUp owns the ledger.*
