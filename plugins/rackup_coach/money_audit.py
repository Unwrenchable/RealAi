"""
ROC money audit — read-only intelligence for RackUp ledger snapshots.

Ownership (locked):
  RackUp: Stripe, USD ledger, splits, payouts, profile balances, all money moves
  RealAI: audit analysis only — never authorize payouts, invent balances, or call Stripe

Default split reference: 45% Players Fund / 35% Operator / 20% RackUp (platform).
Singles-first; doubles/teams via competitor_type extension path.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Optional

from plugins.rackup_coach.roc import (
    FORMAT_SINGLES,
    FORMAT_SCOTCH_DOUBLES,
    FORMAT_SCOTCH_JJ,
    FORMAT_TEAMS_5,
    format_config,
    normalize_format,
)

# Default split as fractions (also accept bps / percent)
DEFAULT_SPLIT = {
    "players_fund": 0.45,
    "operator": 0.35,
    "rackup": 0.20,
}

# Cent tolerance for float/rounding noise
CENT_EPS = 1  # 1 cent

# Entry types (aligned to ROC design vocabulary; host may use aliases)
INFLOW_TYPES = frozenset({
    "SESSION_ENTRY",
    "SEASON_DUES",
    "EVENT_ENTRY",
    "SIDE_POT",
    "PAYMENT",
    "ENTRY_PAYMENT",
    "CREDIT",
    "DEPOSIT",
    "INFLOW",
    "DUES",
    "entry",
    "dues",
    "payment",
    "side_pot",
})
OUTFLOW_TYPES = frozenset({
    "PAYOUT",
    "PRIZE",
    "WITHDRAWAL",
    "OPERATOR_PAYOUT",
    "PLATFORM_FEE",
    "REFUND",
    "DEBIT",
    "payout",
    "prize",
    "refund",
    "withdrawal",
})
HELD_FEE_TYPES = frozenset({
    "PLATFORM_FEE",
    "OPERATOR_REVENUE",
    "HOLDING",
    "PLATFORM_REVENUE",
    "OPERATOR_SHARE",
    "RACKUP_SHARE",
    "platform_fee",
    "operator_fee",
    "held_fee",
})


def _cents(value: Any) -> int:
    """Normalize money to integer cents. Accepts cents int or dollar float."""
    if value is None:
        return 0
    if isinstance(value, bool):
        return 0
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0
    # Heuristic: values with abs < 1e6 and a fractional part → dollars
    # Prefer explicit amount_cents when host provides it
    return int(round(v))


def _entry_cents(entry: dict[str, Any]) -> int:
    if entry.get("amount_cents") is not None:
        return abs(_cents(entry["amount_cents"]))
    if entry.get("amount") is not None:
        a = entry["amount"]
        # If float dollars likely
        try:
            af = float(a)
            if abs(af) < 1_000_000 and ("." in str(a) or isinstance(a, float)):
                return abs(int(round(af * 100)))
        except (TypeError, ValueError):
            pass
        return abs(_cents(a))
    return 0


def _direction(entry: dict[str, Any]) -> str:
    d = str(entry.get("direction") or entry.get("side") or "").upper()
    if d in ("CREDIT", "IN", "INFLOW", "+"):
        return "CREDIT"
    if d in ("DEBIT", "OUT", "OUTFLOW", "-"):
        return "DEBIT"
    # Infer from type / signed amount
    et = str(entry.get("entry_type") or entry.get("type") or entry.get("kind") or "").upper()
    if et in {t.upper() for t in OUTFLOW_TYPES} or "PAYOUT" in et or "REFUND" in et:
        return "DEBIT"
    if et in {t.upper() for t in INFLOW_TYPES} or "PAYMENT" in et or "ENTRY" in et:
        return "CREDIT"
    amt = entry.get("amount_cents", entry.get("amount"))
    try:
        if float(amt) < 0:
            return "DEBIT"
    except (TypeError, ValueError):
        pass
    return "CREDIT"


def _entry_type(entry: dict[str, Any]) -> str:
    return str(
        entry.get("entry_type")
        or entry.get("type")
        or entry.get("kind")
        or entry.get("memo")
        or "UNKNOWN"
    ).upper()


def normalize_split(raw: Any) -> dict[str, float]:
    """
    Accept:
      {"players_fund": 0.45, "operator": 0.35, "rackup": 0.20}
      bps: 4500/3500/2000
      percent: 45/35/20
    """
    if not raw or not isinstance(raw, dict):
        return dict(DEFAULT_SPLIT)

    def pick(*keys: str) -> Any:
        for k in keys:
            if k in raw and raw[k] is not None:
                return raw[k]
        return None

    pf = pick("players_fund", "players", "prize", "players_fund_bps", "players_pct")
    op = pick("operator", "operator_revenue", "operator_bps", "operator_pct")
    rk = pick("rackup", "platform", "platform_revenue", "rackup_bps", "platform_bps", "platform_pct")

    vals = []
    for v in (pf, op, rk):
        if v is None:
            vals.append(None)
        else:
            try:
                vals.append(float(v))
            except (TypeError, ValueError):
                vals.append(None)

    if any(x is None for x in vals):
        return dict(DEFAULT_SPLIT)

    pf_f, op_f, rk_f = vals  # type: ignore
    # bps (sum ~10000)
    if pf_f + op_f + rk_f > 50:  # percent or bps
        if pf_f + op_f + rk_f > 500:  # bps
            s = pf_f + op_f + rk_f
            return {
                "players_fund": pf_f / s,
                "operator": op_f / s,
                "rackup": rk_f / s,
            }
        # percent
        s = pf_f + op_f + rk_f
        return {
            "players_fund": pf_f / s,
            "operator": op_f / s,
            "rackup": rk_f / s,
        }
    s = pf_f + op_f + rk_f
    if s <= 0:
        return dict(DEFAULT_SPLIT)
    if abs(s - 1.0) > 0.02:
        # normalize
        return {
            "players_fund": pf_f / s,
            "operator": op_f / s,
            "rackup": rk_f / s,
        }
    return {"players_fund": pf_f, "operator": op_f, "rackup": rk_f}


def _finding(
    severity: str,
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "severity": severity,  # info | warning | blocker
        "code": code,
        "message": message,
        "details": details or {},
    }


def _competitor_key(row: dict[str, Any]) -> str:
    ct = str(row.get("competitor_type") or row.get("entity_type") or "USER").upper()
    cid = str(
        row.get("competitor_id")
        or row.get("player_id")
        or row.get("team_id")
        or row.get("user_id")
        or row.get("id")
        or ""
    )
    return f"{ct}:{cid}" if cid else ""


def _place(row: dict[str, Any]) -> int | None:
    for k in ("place", "final_place", "rank", "position", "standing"):
        if row.get(k) is not None:
            try:
                return int(row[k])
            except (TypeError, ValueError):
                pass
    return None


def _payout_cents(line: dict[str, Any]) -> int:
    if line.get("payout_cents") is not None:
        return abs(_cents(line["payout_cents"]))
    if line.get("amount_cents") is not None:
        return abs(_cents(line["amount_cents"]))
    if line.get("amount") is not None:
        return _entry_cents(line)
    return 0


# ---------------------------------------------------------------------------
# 1) ledger_audit
# ---------------------------------------------------------------------------

def ledger_audit(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Audit a session/season ledger snapshot before payout release.

    Never authorizes payouts. Never invents balances.
    """
    payload = payload or {}
    findings: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []

    roc_league_id = payload.get("roc_league_id") or payload.get("league_id")
    session_id = payload.get("session_id")
    season_id = payload.get("season_id")
    fmt = normalize_format(payload.get("format") or payload.get("season_format")) or FORMAT_SINGLES
    fcfg = format_config(fmt)
    split = normalize_split(
        payload.get("configured_split")
        or payload.get("split")
        or payload.get("split_snapshot")
    )

    entries = list(payload.get("ledger_entries") or payload.get("entries") or [])
    payout_lines = list(payload.get("payout_lines") or payload.get("payouts") or [])
    standings = list(payload.get("standings") or payload.get("session_standings") or [])
    payments = list(payload.get("payments") or [])

    if not entries and not payments and not payout_lines:
        blockers.append(
            _finding(
                "blocker",
                "empty_snapshot",
                "No ledger_entries, payments, or payout_lines provided — cannot audit.",
            )
        )
        return _audit_envelope(
            ok=False,
            ability="ledger_audit",
            findings=blockers,
            warnings=warnings,
            blockers=blockers,
            meta={
                "roc_league_id": roc_league_id,
                "session_id": session_id,
                "season_id": season_id,
                "format": fmt,
            },
            extras={"split_expected": split},
        )

    # --- Classify ledger flows ---
    inflow_cents = 0
    outflow_cents = 0
    held_fee_cents = 0
    by_type: Counter[str] = Counter()
    idempotency_keys: list[str] = []
    payment_ids: list[str] = []
    payee_payouts: dict[str, int] = defaultdict(int)
    credit_ids: list[str] = []

    for e in entries:
        if not isinstance(e, dict):
            warnings.append(
                _finding("warning", "malformed_entry", "Non-object ledger entry skipped.")
            )
            continue
        cents = _entry_cents(e)
        et = _entry_type(e)
        by_type[et] += cents
        direction = _direction(e)
        ik = e.get("idempotency_key") or e.get("id")
        if ik:
            idempotency_keys.append(str(ik))
        if e.get("payment_id"):
            payment_ids.append(str(e["payment_id"]))
        if e.get("payout_id"):
            credit_ids.append(str(e["payout_id"]))

        if et in {t.upper() for t in HELD_FEE_TYPES} or "FEE" in et or "REVENUE" in et:
            held_fee_cents += cents
            if direction == "DEBIT":
                outflow_cents += cents
            continue

        if direction == "CREDIT":
            inflow_cents += cents
        else:
            outflow_cents += cents
            if "PAYOUT" in et or "PRIZE" in et:
                ck = _competitor_key(e)
                if ck:
                    payee_payouts[ck] += cents

    # Payments array (host may send separate from ledger)
    payment_in_cents = 0
    payment_status_counts: Counter[str] = Counter()
    payment_id_list: list[str] = []
    for p in payments:
        if not isinstance(p, dict):
            continue
        st = str(p.get("status") or "UNKNOWN").upper()
        payment_status_counts[st] += 1
        pid = p.get("id") or p.get("payment_id")
        if pid:
            payment_id_list.append(str(pid))
        if st in ("SUCCEEDED", "SUCCESS", "PAID", "COMPLETE", "COMPLETED"):
            payment_in_cents += _entry_cents(p)

    if payment_in_cents and not inflow_cents:
        inflow_cents = payment_in_cents
        findings.append(
            _finding(
                "info",
                "inflow_from_payments",
                "Inflows derived from payments[] (no CREDIT ledger rows).",
                details={"payment_in_cents": payment_in_cents},
            )
        )
    elif payment_in_cents and inflow_cents:
        if abs(payment_in_cents - inflow_cents) > max(CENT_EPS, int(inflow_cents * 0.01)):
            warnings.append(
                _finding(
                    "warning",
                    "payments_vs_ledger_inflow",
                    "Succeeded payments total does not match ledger CREDIT inflows.",
                    details={
                        "payments_cents": payment_in_cents,
                        "ledger_inflow_cents": inflow_cents,
                        "diff_cents": payment_in_cents - inflow_cents,
                    },
                )
            )

    # Payout lines total
    payout_lines_cents = sum(_payout_cents(pl) for pl in payout_lines if isinstance(pl, dict))
    for pl in payout_lines:
        if not isinstance(pl, dict):
            continue
        ck = _competitor_key(pl)
        if ck:
            payee_payouts[ck] += 0  # ensure key
            # prefer explicit line amounts for payee map when lines present
        if ck and _payout_cents(pl):
            # rebuild from lines if we have them
            pass

    if payout_lines:
        payee_from_lines: dict[str, int] = defaultdict(int)
        for pl in payout_lines:
            if not isinstance(pl, dict):
                continue
            ck = _competitor_key(pl)
            if ck:
                payee_from_lines[ck] += _payout_cents(pl)
        if payee_from_lines:
            payee_payouts = payee_from_lines

    # --- Split math ---
    # Eligible inflow for split = session entries (host may pass eligible_inflow_cents)
    eligible = payload.get("eligible_inflow_cents")
    if eligible is not None:
        eligible_cents = abs(_cents(eligible))
    else:
        eligible_cents = inflow_cents

    expected_players = int(round(eligible_cents * split["players_fund"]))
    expected_operator = int(round(eligible_cents * split["operator"]))
    expected_rackup = int(round(eligible_cents * split["rackup"]))
    # Fix rounding drift to sum exactly
    drift = eligible_cents - (expected_players + expected_operator + expected_rackup)
    expected_players += drift

    split_check = {
        "configured": split,
        "eligible_inflow_cents": eligible_cents,
        "expected": {
            "players_fund_cents": expected_players,
            "operator_cents": expected_operator,
            "rackup_cents": expected_rackup,
        },
        "observed": {
            "payout_lines_cents": payout_lines_cents,
            "held_fee_cents": held_fee_cents,
            "outflow_cents": outflow_cents,
            "inflow_cents": inflow_cents,
        },
    }

    # Players fund should approximately equal prize payout lines
    if payout_lines_cents and eligible_cents:
        diff = payout_lines_cents - expected_players
        if abs(diff) > max(CENT_EPS * 5, int(expected_players * 0.02) if expected_players else 0):
            sev = "blocker" if abs(diff) > max(100, int(expected_players * 0.05)) else "warning"
            f = _finding(
                sev,
                "split_players_fund_mismatch",
                (
                    f"Payout lines total {payout_lines_cents}¢ vs expected players fund "
                    f"{expected_players}¢ (split {split['players_fund']:.0%})."
                ),
                details={"diff_cents": diff, "expected_players_fund_cents": expected_players},
            )
            (blockers if sev == "blocker" else warnings).append(f)

    # Sum check: payments in vs payouts + held fees
    accounted = payout_lines_cents + held_fee_cents
    if not held_fee_cents and eligible_cents and payout_lines_cents:
        # infer held as operator+rackup share
        accounted = payout_lines_cents + expected_operator + expected_rackup
        split_check["observed"]["held_fee_cents_inferred"] = expected_operator + expected_rackup

    if eligible_cents and accounted:
        bal_diff = eligible_cents - accounted
        if abs(bal_diff) > max(CENT_EPS * 5, int(eligible_cents * 0.02)):
            sev = "blocker" if abs(bal_diff) > max(200, int(eligible_cents * 0.05)) else "warning"
            f = _finding(
                sev,
                "inflow_vs_outflow_imbalance",
                (
                    f"Eligible inflows {eligible_cents}¢ vs payouts+fees {accounted}¢ "
                    f"(diff {bal_diff}¢)."
                ),
                details={
                    "eligible_inflow_cents": eligible_cents,
                    "payout_plus_fees_cents": accounted,
                    "diff_cents": bal_diff,
                },
            )
            (blockers if sev == "blocker" else warnings).append(f)
        else:
            findings.append(
                _finding(
                    "info",
                    "inflow_outflow_balanced",
                    "Inflows approximately balance payout lines + held fees.",
                    details={"diff_cents": bal_diff},
                )
            )

    # --- Duplicates ---
    idemp_counts = Counter(idempotency_keys)
    dup_keys = [k for k, n in idemp_counts.items() if n > 1]
    if dup_keys:
        blockers.append(
            _finding(
                "blocker",
                "duplicate_idempotency_keys",
                f"Duplicate ledger idempotency keys detected ({len(dup_keys)}).",
                details={"keys": dup_keys[:20]},
            )
        )

    pay_id_counts = Counter(payment_id_list + payment_ids)
    dup_pays = [k for k, n in pay_id_counts.items() if n > 1]
    if dup_pays:
        warnings.append(
            _finding(
                "warning",
                "duplicate_payment_ids",
                f"Payment ids appear more than once ({len(dup_pays)}).",
                details={"payment_ids": dup_pays[:20]},
            )
        )

    # Double payout risk: same competitor multiple paid lines
    paid_status_lines = [
        pl
        for pl in payout_lines
        if isinstance(pl, dict)
        and str(pl.get("payout_status") or pl.get("status") or "").upper()
        in ("PAID", "SUCCEEDED", "COMPLETE", "COMPLETED", "PROJECTED", "PENDING", "")
    ]
    payee_line_counts: Counter[str] = Counter()
    for pl in paid_status_lines:
        ck = _competitor_key(pl)
        if ck:
            payee_line_counts[ck] += 1
    multi = {k: n for k, n in payee_line_counts.items() if n > 1}
    if multi:
        warnings.append(
            _finding(
                "warning",
                "multiple_payout_lines_per_competitor",
                "Some competitors have multiple payout lines — verify not double-paid.",
                details={"competitors": multi},
            )
        )

    # --- Standings vs payees ---
    winner_keys: set[str] = set()
    place_map: dict[str, int] = {}
    for s in standings:
        if not isinstance(s, dict):
            continue
        ck = _competitor_key(s)
        pl = _place(s)
        if ck and pl is not None:
            place_map[ck] = pl
            if pl == 1:
                winner_keys.add(ck)

    paid_keys = {k for k, v in payee_payouts.items() if v > 0}
    if place_map and paid_keys:
        # Paid but not in standings
        ghosts = sorted(paid_keys - set(place_map.keys()))
        if ghosts:
            blockers.append(
                _finding(
                    "blocker",
                    "paid_not_in_standings",
                    "Payout recipients not found in standings.",
                    details={"competitors": ghosts[:20]},
                )
            )
        # Top places with zero payout when lines exist
        if payout_lines_cents:
            missing_winners = []
            for ck, pl in place_map.items():
                if pl == 1 and ck not in paid_keys:
                    missing_winners.append(ck)
            if missing_winners:
                blockers.append(
                    _finding(
                        "blocker",
                        "missing_winner_payout",
                        "1st place has no payout line.",
                        details={"competitors": missing_winners},
                    )
                )

    # Format competitor_type checks (singles first)
    if fmt == FORMAT_SINGLES and payout_lines:
        for pl in payout_lines:
            if not isinstance(pl, dict):
                continue
            ct = str(pl.get("competitor_type") or "USER").upper()
            if ct == "TEAM":
                warnings.append(
                    _finding(
                        "warning",
                        "singles_team_competitor",
                        "SINGLES session has TEAM competitor on a payout line.",
                        details={"line": _competitor_key(pl)},
                    )
                )
                break
    if fmt in (FORMAT_SCOTCH_DOUBLES, FORMAT_SCOTCH_JJ, FORMAT_TEAMS_5) and payout_lines:
        for pl in payout_lines:
            if not isinstance(pl, dict):
                continue
            ct = str(pl.get("competitor_type") or "").upper()
            if ct == "USER" and fcfg.get("competitor_type") == "TEAM":
                warnings.append(
                    _finding(
                        "warning",
                        "team_format_user_payout",
                        f"{fmt} typically pays TEAM competitors — found USER payout line.",
                        details={"line": _competitor_key(pl), "format": fmt},
                    )
                )
                break

    all_findings = findings + warnings + blockers
    plain = _plain_language(all_findings, context="ledger")

    ok = len(blockers) == 0
    return _audit_envelope(
        ok=ok,
        ability="ledger_audit",
        findings=all_findings,
        warnings=warnings,
        blockers=blockers,
        meta={
            "roc_league_id": roc_league_id,
            "session_id": session_id,
            "season_id": season_id,
            "format": fmt,
            "format_config": fcfg,
        },
        extras={
            "split_check": split_check,
            "totals": {
                "inflow_cents": inflow_cents,
                "payment_in_cents": payment_in_cents,
                "payout_lines_cents": payout_lines_cents,
                "held_fee_cents": held_fee_cents,
                "outflow_cents": outflow_cents,
                "eligible_inflow_cents": eligible_cents,
            },
            "by_entry_type_cents": dict(by_type),
            "payee_payouts_cents": dict(payee_payouts),
            "payment_status_counts": dict(payment_status_counts),
            "plain_language": plain,
            "gate": {
                "recommend_before_auto_payout": True,
                "hard_block_if_blockers": True,
                "soft_warn_if_warnings_only": True,
                "authorize_payout": False,
                "note": (
                    "RackUp must call ledger_audit before auto-payout release. "
                    "RealAI never authorizes money movement."
                ),
            },
        },
    )


# ---------------------------------------------------------------------------
# 2) payout_sanity
# ---------------------------------------------------------------------------

def payout_sanity(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Check final/projected payout lines against standings and format.
    """
    payload = payload or {}
    warnings: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    fix_items: list[dict[str, Any]] = []

    fmt = normalize_format(payload.get("format") or payload.get("season_format")) or FORMAT_SINGLES
    fcfg = format_config(fmt)
    standings = list(payload.get("standings") or payload.get("final_standings") or [])
    payout_lines = list(
        payload.get("payout_lines")
        or payload.get("projected_payout_lines")
        or payload.get("payouts")
        or []
    )
    structure = payload.get("payout_structure") or payload.get("payout_structure_snapshot") or {}

    if not standings:
        blockers.append(
            _finding("blocker", "no_standings", "Standings required for payout sanity.")
        )
    if not payout_lines:
        blockers.append(
            _finding(
                "blocker",
                "no_payout_lines",
                "No payout lines (projected or final) provided.",
            )
        )

    # Build place → competitor
    by_place: dict[int, list[str]] = defaultdict(list)
    by_key: dict[str, dict[str, Any]] = {}
    for s in standings:
        if not isinstance(s, dict):
            continue
        ck = _competitor_key(s)
        pl = _place(s)
        if ck:
            by_key[ck] = s
        if ck and pl is not None:
            by_place[pl].append(ck)

    # Duplicate places (except ties — host may mark tie)
    for pl, keys in by_place.items():
        if len(keys) > 1 and not payload.get("allow_ties"):
            warnings.append(
                _finding(
                    "warning",
                    "shared_place",
                    f"Place {pl} has {len(keys)} competitors — confirm ties/split prizes.",
                    details={"place": pl, "competitors": keys},
                )
            )

    # Map place table from structure if present
    # e.g. {"1": 0.50, "2": 0.30, "3": 0.20} of players fund or absolute cents
    place_amounts: dict[int, int] = {}
    if isinstance(structure, dict):
        places_raw = structure.get("places") or structure.get("table") or structure
        if isinstance(places_raw, dict):
            for k, v in places_raw.items():
                try:
                    pi = int(str(k).replace("place_", "").replace("p", ""))
                except ValueError:
                    continue
                if isinstance(v, dict):
                    place_amounts[pi] = _payout_cents(v)
                else:
                    # fraction of pot or cents
                    try:
                        fv = float(v)
                        if 0 < fv <= 1:
                            pot = int(
                                payload.get("players_fund_cents")
                                or payload.get("prize_pool_cents")
                                or 0
                            )
                            place_amounts[pi] = int(round(pot * fv)) if pot else 0
                        else:
                            place_amounts[pi] = abs(_cents(fv))
                    except (TypeError, ValueError):
                        pass

    line_issues = []
    seen_keys: Counter[str] = Counter()
    total_lines = 0
    for i, pl in enumerate(payout_lines):
        if not isinstance(pl, dict):
            blockers.append(
                _finding("blocker", "malformed_payout_line", f"Payout line[{i}] is not an object.")
            )
            continue
        ck = _competitor_key(pl)
        place = _place(pl)
        amt = _payout_cents(pl)
        total_lines += amt
        if ck:
            seen_keys[ck] += 1

        if not ck:
            blockers.append(
                _finding(
                    "blocker",
                    "payout_missing_competitor",
                    f"Payout line[{i}] missing competitor_id/player_id.",
                    details={"index": i},
                )
            )
            fix_items.append(
                {
                    "index": i,
                    "action": "set_competitor",
                    "reason": "missing competitor identity",
                }
            )
            continue

        # Rank match
        standing = by_key.get(ck)
        if standing is None:
            blockers.append(
                _finding(
                    "blocker",
                    "payout_not_in_standings",
                    f"Payout for {ck} has no standing row.",
                    details={"competitor": ck, "index": i, "amount_cents": amt},
                )
            )
            fix_items.append(
                {
                    "index": i,
                    "competitor": ck,
                    "action": "remove_or_add_standing",
                    "reason": "payee not in standings",
                    "amount_cents": amt,
                }
            )
        else:
            st_place = _place(standing)
            if place is not None and st_place is not None and place != st_place:
                blockers.append(
                    _finding(
                        "blocker",
                        "place_mismatch",
                        f"{ck}: payout place {place} ≠ standings place {st_place}.",
                        details={
                            "competitor": ck,
                            "payout_place": place,
                            "standing_place": st_place,
                            "amount_cents": amt,
                        },
                    )
                )
                fix_items.append(
                    {
                        "index": i,
                        "competitor": ck,
                        "action": "fix_place",
                        "from_place": place,
                        "to_place": st_place,
                        "amount_cents": amt,
                    }
                )

        # Amount vs structure
        if place is not None and place in place_amounts and place_amounts[place] > 0:
            exp = place_amounts[place]
            if abs(amt - exp) > max(CENT_EPS * 5, int(exp * 0.02)):
                warnings.append(
                    _finding(
                        "warning",
                        "amount_vs_structure",
                        f"{ck} place {place}: line {amt}¢ vs structure {exp}¢.",
                        details={
                            "competitor": ck,
                            "place": place,
                            "line_cents": amt,
                            "structure_cents": exp,
                        },
                    )
                )
                fix_items.append(
                    {
                        "index": i,
                        "competitor": ck,
                        "action": "adjust_amount",
                        "from_cents": amt,
                        "to_cents": exp,
                        "reason": "payout_structure mismatch",
                    }
                )

        # Format competitor type
        ct = str(pl.get("competitor_type") or "USER").upper()
        expected_ct = str(fcfg.get("competitor_type") or "USER").upper()
        if fmt == FORMAT_SINGLES and ct == "TEAM":
            warnings.append(
                _finding(
                    "warning",
                    "format_competitor_type",
                    "Singles payout line uses TEAM competitor_type.",
                    details={"competitor": ck, "index": i},
                )
            )
            fix_items.append(
                {
                    "index": i,
                    "competitor": ck,
                    "action": "set_competitor_type",
                    "to": "USER",
                    "reason": "SINGLES format",
                }
            )
        elif expected_ct == "TEAM" and ct == "USER" and fmt != FORMAT_SINGLES:
            warnings.append(
                _finding(
                    "warning",
                    "format_competitor_type",
                    f"{fmt} expects TEAM payout entity; line is USER.",
                    details={"competitor": ck, "format": fmt},
                )
            )
            fix_items.append(
                {
                    "index": i,
                    "competitor": ck,
                    "action": "verify_team_vs_user",
                    "format": fmt,
                }
            )

        line_issues.append(
            {
                "index": i,
                "competitor": ck,
                "place": place,
                "amount_cents": amt,
                "ok": ck in by_key
                and (
                    place is None
                    or _place(by_key[ck]) is None
                    or place == _place(by_key[ck])
                ),
            }
        )

    # Missing places that structure says should be paid
    if place_amounts and by_place:
        for pl, exp_amt in place_amounts.items():
            if exp_amt <= 0:
                continue
            keys = by_place.get(pl) or []
            paid_for_place = [
                ln
                for ln in payout_lines
                if isinstance(ln, dict) and _place(ln) == pl and _payout_cents(ln) > 0
            ]
            if keys and not paid_for_place:
                blockers.append(
                    _finding(
                        "blocker",
                        "missing_place_payout",
                        f"Place {pl} has standings but no payout line (structure expects {exp_amt}¢).",
                        details={"place": pl, "competitors": keys, "expected_cents": exp_amt},
                    )
                )
                fix_items.append(
                    {
                        "action": "add_payout_line",
                        "place": pl,
                        "competitors": keys,
                        "amount_cents": exp_amt,
                    }
                )

    # Confidence
    if blockers:
        confidence = 0.25
    elif warnings:
        confidence = 0.65
    else:
        confidence = 0.92
    if not standings or not payout_lines:
        confidence = min(confidence, 0.2)

    ok = len(blockers) == 0
    all_findings = findings + warnings + blockers
    plain = _plain_language(all_findings, context="payout")

    return _audit_envelope(
        ok=ok,
        ability="payout_sanity",
        findings=all_findings,
        warnings=warnings,
        blockers=blockers,
        meta={
            "roc_league_id": payload.get("roc_league_id"),
            "session_id": payload.get("session_id"),
            "season_id": payload.get("season_id"),
            "format": fmt,
            "format_config": fcfg,
        },
        extras={
            "confidence": confidence,
            "ranks_match_standings": ok and not any(
                f["code"] == "place_mismatch" for f in blockers
            ),
            "total_payout_lines_cents": total_lines,
            "line_checks": line_issues,
            "fix_before_release": fix_items,
            "plain_language": plain,
            "gate": {
                "recommend_before_auto_payout": True,
                "release_safe": ok and confidence >= 0.8,
                "authorize_payout": False,
                "note": (
                    "If ok and release_safe, RackUp may proceed with auto-payout. "
                    "RealAI does not authorize or execute payouts."
                ),
            },
        },
    )


# ---------------------------------------------------------------------------
# 3) money_anomaly
# ---------------------------------------------------------------------------

def money_anomaly(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    Scan player or operator payment history window for anomalies.
    """
    payload = payload or {}
    findings: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []

    history = list(
        payload.get("payment_history")
        or payload.get("history")
        or payload.get("transactions")
        or payload.get("payments")
        or []
    )
    role = str(payload.get("role") or payload.get("subject_role") or "PLAYER").upper()
    subject_id = str(
        payload.get("subject_id")
        or payload.get("player_id")
        or payload.get("operator_id")
        or payload.get("user_id")
        or ""
    )
    window_days = int(payload.get("window_days") or payload.get("days") or 30)

    if not history:
        warnings.append(
            _finding(
                "warning",
                "empty_history",
                "No payment history in window — nothing to score.",
            )
        )
        return _audit_envelope(
            ok=True,
            ability="money_anomaly",
            findings=warnings,
            warnings=warnings,
            blockers=[],
            meta={"subject_id": subject_id, "role": role, "window_days": window_days},
            extras={
                "risk_score": 0,
                "risk_level": "none",
                "recommended_human_review": False,
                "anomalies": [],
                "authorize_payout": False,
            },
        )

    risk = 0
    anomalies: list[dict[str, Any]] = []

    # Normalize events
    events = []
    for h in history:
        if not isinstance(h, dict):
            continue
        st = str(h.get("status") or "").upper()
        kind = str(h.get("type") or h.get("entry_type") or h.get("kind") or "PAYMENT").upper()
        cents = _entry_cents(h)
        tx = h.get("provider_ref") or h.get("tx_ref") or h.get("stripe_id") or h.get("external_id")
        events.append(
            {
                "status": st,
                "kind": kind,
                "cents": cents,
                "tx_ref": tx,
                "id": h.get("id") or h.get("payment_id"),
                "created_at": h.get("created_at") or h.get("timestamp") or h.get("at"),
                "raw": h,
            }
        )

    # Refund loops: payment success → refund → success same amount pattern
    successes = [e for e in events if e["status"] in ("SUCCEEDED", "SUCCESS", "PAID", "COMPLETED")]
    refunds = [
        e
        for e in events
        if e["status"] in ("REFUNDED", "REFUND") or "REFUND" in e["kind"]
    ]
    if len(refunds) >= 2 and len(successes) >= 2:
        risk += 25
        anomalies.append(
            {
                "code": "refund_loop_suspected",
                "message": f"{len(refunds)} refunds and {len(successes)} successes in window.",
                "severity": "warning",
            }
        )
        warnings.append(
            _finding(
                "warning",
                "refund_loop_suspected",
                "Multiple refunds interleaved with successes — review for refund loops.",
                details={"refunds": len(refunds), "successes": len(successes)},
            )
        )

    # Failed then success spikes
    fails = [
        e
        for e in events
        if e["status"] in ("FAILED", "FAIL", "CANCELED", "CANCELLED", "DECLINED")
    ]
    if len(fails) >= 3 and len(successes) >= 1:
        # same amount retries
        fail_amts = Counter(e["cents"] for e in fails if e["cents"])
        success_amts = Counter(e["cents"] for e in successes if e["cents"])
        overlap = set(fail_amts) & set(success_amts)
        if overlap or len(fails) >= 5:
            risk += 20
            anomalies.append(
                {
                    "code": "failed_then_success_spike",
                    "message": (
                        f"{len(fails)} failed pays then success(es) — card testing or retries."
                    ),
                    "severity": "warning",
                    "overlap_amounts_cents": list(overlap)[:10],
                }
            )
            warnings.append(
                _finding(
                    "warning",
                    "failed_then_success_spike",
                    "Repeated failed payments followed by success — possible card testing.",
                    details={"failed": len(fails), "succeeded": len(successes)},
                )
            )

    # Missing tx refs on succeeded money moves
    missing_tx = [
        e
        for e in successes
        if not e["tx_ref"] and e["cents"] > 0 and e["kind"] not in ("COMP", "MANUAL_ADJ")
    ]
    if missing_tx:
        risk += 15 + min(20, len(missing_tx) * 3)
        anomalies.append(
            {
                "code": "missing_tx_refs",
                "message": f"{len(missing_tx)} succeeded payments lack provider/tx refs.",
                "severity": "warning" if len(missing_tx) < 3 else "blocker",
                "count": len(missing_tx),
            }
        )
        f = _finding(
            "blocker" if len(missing_tx) >= 3 else "warning",
            "missing_tx_refs",
            "Succeeded payments missing Stripe/provider transaction references.",
            details={"count": len(missing_tx), "ids": [e.get("id") for e in missing_tx[:15]]},
        )
        (blockers if f["severity"] == "blocker" else warnings).append(f)

    # Operator withdraw pattern
    if role in ("OPERATOR", "ADMIN", "PLATFORM"):
        withdraws = [
            e
            for e in events
            if "WITHDRAW" in e["kind"]
            or e["kind"] in ("OPERATOR_PAYOUT", "OPERATOR_REVENUE", "PAYOUT")
            or str(e["raw"].get("direction") or "").upper() == "DEBIT"
            and e["cents"] > 0
            and role == "OPERATOR"
        ]
        # Prefer explicit withdraw types
        withdraws = [
            e
            for e in events
            if any(
                x in e["kind"]
                for x in ("WITHDRAW", "OPERATOR_PAYOUT", "OPERATOR_REVENUE", "TRANSFER_OUT")
            )
        ]
        total_w = sum(e["cents"] for e in withdraws)
        if len(withdraws) >= 5:
            risk += 20
            anomalies.append(
                {
                    "code": "operator_withdraw_frequency",
                    "message": f"{len(withdraws)} operator withdrawals in window.",
                    "severity": "warning",
                    "total_cents": total_w,
                }
            )
            warnings.append(
                _finding(
                    "warning",
                    "operator_withdraw_frequency",
                    "Unusual operator withdrawal frequency — human review recommended.",
                    details={"count": len(withdraws), "total_cents": total_w},
                )
            )
        # Large single withdraw
        if withdraws:
            max_w = max(e["cents"] for e in withdraws)
            median_hint = sorted(e["cents"] for e in withdraws)[len(withdraws) // 2]
            if max_w > max(50_000, median_hint * 5):  # >$500 or 5× median
                risk += 25
                anomalies.append(
                    {
                        "code": "operator_withdraw_spike",
                        "message": f"Large operator withdrawal {max_w}¢ vs typical ~{median_hint}¢.",
                        "severity": "warning",
                    }
                )
                warnings.append(
                    _finding(
                        "warning",
                        "operator_withdraw_spike",
                        "Operator withdrawal spike relative to window baseline.",
                        details={"max_cents": max_w, "median_cents": median_hint},
                    )
                )

    # Duplicate payment ids
    ids = [str(e["id"]) for e in events if e.get("id")]
    dup = [i for i, n in Counter(ids).items() if n > 1]
    if dup:
        risk += 30
        anomalies.append(
            {
                "code": "duplicate_payment_ids",
                "message": f"Duplicate payment ids in history: {len(dup)}.",
                "severity": "blocker",
            }
        )
        blockers.append(
            _finding(
                "blocker",
                "duplicate_payment_ids",
                "Duplicate payment identifiers in history window.",
                details={"ids": dup[:20]},
            )
        )

    # Velocity: many succeeds same day (if timestamps allow)
    # Soft heuristic on raw count
    if len(successes) >= 15:
        risk += 15
        anomalies.append(
            {
                "code": "high_payment_velocity",
                "message": f"{len(successes)} successful payments in {window_days}d window.",
                "severity": "info",
            }
        )
        findings.append(
            _finding(
                "info",
                "high_payment_velocity",
                "High payment velocity — confirm expected for busy league nights.",
                details={"successes": len(successes), "window_days": window_days},
            )
        )

    risk = min(100, risk)
    if risk >= 70:
        risk_level = "critical"
    elif risk >= 45:
        risk_level = "high"
    elif risk >= 25:
        risk_level = "elevated"
    elif risk >= 10:
        risk_level = "low"
    else:
        risk_level = "none"

    review = risk >= 25 or len(blockers) > 0
    all_findings = findings + warnings + blockers
    plain = _plain_language(all_findings, context="anomaly")

    return _audit_envelope(
        ok=len(blockers) == 0,
        ability="money_anomaly",
        findings=all_findings,
        warnings=warnings,
        blockers=blockers,
        meta={
            "subject_id": subject_id,
            "role": role,
            "window_days": window_days,
            "event_count": len(events),
        },
        extras={
            "risk_score": risk,
            "risk_level": risk_level,
            "recommended_human_review": review,
            "anomalies": anomalies,
            "counts": {
                "events": len(events),
                "successes": len(successes),
                "failures": len(fails),
                "refunds": len(refunds),
                "missing_tx_refs": len(missing_tx),
            },
            "plain_language": plain,
            "gate": {
                "authorize_payout": False,
                "recommend_hold_payouts_if_critical": risk_level == "critical",
                "note": "Advisory only — RackUp decides holds; RealAI never moves money.",
            },
        },
    )


# ---------------------------------------------------------------------------
# Shared envelope
# ---------------------------------------------------------------------------

def _plain_language(findings: list[dict[str, Any]], *, context: str) -> list[str]:
    lines = []
    for f in findings:
        sev = f.get("severity", "info")
        msg = f.get("message") or f.get("code")
        if sev == "blocker":
            lines.append(f"BLOCKER: {msg}")
        elif sev == "warning":
            lines.append(f"Warning: {msg}")
        else:
            lines.append(str(msg))
    if not lines:
        if context == "ledger":
            lines.append("Ledger snapshot looks consistent — no blockers found.")
        elif context == "payout":
            lines.append("Payout lines align with standings — safe for RackUp to consider release.")
        else:
            lines.append("No material money anomalies in the provided window.")
    return lines


def _audit_envelope(
    *,
    ok: bool,
    ability: str,
    findings: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
    blockers: list[dict[str, Any]],
    meta: dict[str, Any],
    extras: dict[str, Any],
) -> dict[str, Any]:
    return {
        "ok": ok,
        "ability": ability,
        "status": "pass" if ok else "fail",
        "owns_ledger": False,
        "owns_payouts": False,
        "authorize_payout": False,
        "read_only": True,
        "provider": "realai",
        "plugin": "rackup-coach",
        "meta": meta,
        "summary": {
            "ok": ok,
            "warning_count": len(warnings),
            "blocker_count": len(blockers),
            "finding_count": len(findings),
        },
        "warnings": warnings,
        "blockers": blockers,
        "findings": findings,
        **extras,
        "boundary": {
            "realai": "audit analysis only",
            "rackup": "Stripe, ledger writes, split execution, payout release",
            "never": [
                "authorize_payout",
                "call_stripe",
                "invent_balances",
                "move_money",
            ],
        },
    }
