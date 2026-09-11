"""ROC money audit abilities — read-only ledger intelligence."""
from __future__ import annotations

from plugins.rackup_coach import invoke, METADATA


def _pass_snapshot():
    # $100 entries × 10 = $1000 = 100000 cents
    # 45% players = 45000, 35% op = 35000, 20% platform = 20000
    return {
        "ability": "ledger_audit",
        "roc_league_id": "roc_test",
        "session_id": "ses_1",
        "format": "SINGLES",
        "configured_split": {"players_fund": 0.45, "operator": 0.35, "rackup": 0.20},
        "eligible_inflow_cents": 100_000,
        "payments": [
            {"id": f"pay_{i}", "status": "SUCCEEDED", "amount_cents": 10_000}
            for i in range(10)
        ],
        "ledger_entries": [
            {
                "id": f"le_in_{i}",
                "direction": "CREDIT",
                "entry_type": "SESSION_ENTRY",
                "amount_cents": 10_000,
                "idempotency_key": f"entry_{i}",
                "payment_id": f"pay_{i}",
            }
            for i in range(10)
        ]
        + [
            {
                "id": "le_fee_op",
                "direction": "DEBIT",
                "entry_type": "OPERATOR_REVENUE",
                "amount_cents": 35_000,
                "idempotency_key": "fee_op",
            },
            {
                "id": "le_fee_pl",
                "direction": "DEBIT",
                "entry_type": "PLATFORM_REVENUE",
                "amount_cents": 20_000,
                "idempotency_key": "fee_pl",
            },
        ],
        "payout_lines": [
            {
                "competitor_type": "USER",
                "competitor_id": "u1",
                "player_id": "u1",
                "place": 1,
                "payout_cents": 25_000,
                "payout_status": "PROJECTED",
            },
            {
                "competitor_type": "USER",
                "competitor_id": "u2",
                "player_id": "u2",
                "place": 2,
                "payout_cents": 15_000,
                "payout_status": "PROJECTED",
            },
            {
                "competitor_type": "USER",
                "competitor_id": "u3",
                "player_id": "u3",
                "place": 3,
                "payout_cents": 5_000,
                "payout_status": "PROJECTED",
            },
        ],
        "standings": [
            {"player_id": "u1", "competitor_type": "USER", "final_place": 1},
            {"player_id": "u2", "competitor_type": "USER", "final_place": 2},
            {"player_id": "u3", "competitor_type": "USER", "final_place": 3},
            {"player_id": "u4", "competitor_type": "USER", "final_place": 4},
        ],
        "organs_enabled": False,
    }


def test_metadata_money_audit():
    assert "ledger_audit" in METADATA["methods"]
    assert METADATA["roc"]["money_audit"]["authorize_payout"] is False


def test_ledger_audit_pass():
    r = invoke(_pass_snapshot())
    assert r["ok"] is True
    res = r["result"]
    assert res["ok"] is True
    assert res["status"] == "pass"
    assert res["authorize_payout"] is False
    assert res["owns_ledger"] is False
    assert res["summary"]["blocker_count"] == 0
    assert res["split_check"]["expected"]["players_fund_cents"] == 45_000
    assert res["totals"]["payout_lines_cents"] == 45_000
    assert res["gate"]["recommend_before_auto_payout"] is True


def test_ledger_audit_fail_wrong_split_and_ghost():
    snap = _pass_snapshot()
    # Blow up players fund vs expected
    snap["payout_lines"] = [
        {
            "competitor_type": "USER",
            "competitor_id": "ghost",
            "player_id": "ghost",
            "place": 1,
            "payout_cents": 80_000,
            "payout_status": "PROJECTED",
        }
    ]
    r = invoke(snap)
    res = r["result"]
    assert res["ok"] is False
    assert res["status"] == "fail"
    codes = {b["code"] for b in res["blockers"]}
    assert "paid_not_in_standings" in codes or "split_players_fund_mismatch" in codes
    assert res["authorize_payout"] is False


def test_ledger_audit_duplicate_idempotency():
    snap = _pass_snapshot()
    snap["ledger_entries"][0]["idempotency_key"] = "dup"
    snap["ledger_entries"][1]["idempotency_key"] = "dup"
    r = invoke(snap)
    res = r["result"]
    assert res["ok"] is False
    assert any(b["code"] == "duplicate_idempotency_keys" for b in res["blockers"])


def test_payout_sanity_pass():
    r = invoke(
        {
            "ability": "payout_sanity",
            "format": "SINGLES",
            "session_id": "ses_1",
            "players_fund_cents": 45_000,
            "payout_structure": {"places": {"1": 25_000, "2": 15_000, "3": 5_000}},
            "standings": [
                {"player_id": "u1", "final_place": 1},
                {"player_id": "u2", "final_place": 2},
                {"player_id": "u3", "final_place": 3},
            ],
            "payout_lines": [
                {"player_id": "u1", "place": 1, "payout_cents": 25_000},
                {"player_id": "u2", "place": 2, "payout_cents": 15_000},
                {"player_id": "u3", "place": 3, "payout_cents": 5_000},
            ],
            "organs_enabled": False,
        }
    )
    assert r["ok"] is True
    res = r["result"]
    assert res["ok"] is True
    assert res["ranks_match_standings"] is True
    assert res["gate"]["release_safe"] is True
    assert res["confidence"] >= 0.8
    assert res["authorize_payout"] is False


def test_payout_sanity_fail_place_mismatch():
    r = invoke(
        {
            "ability": "payout_sanity",
            "format": "SINGLES",
            "standings": [
                {"player_id": "u1", "final_place": 1},
                {"player_id": "u2", "final_place": 2},
            ],
            "payout_lines": [
                {"player_id": "u1", "place": 2, "payout_cents": 10_000},  # wrong place
                {"player_id": "u2", "place": 1, "payout_cents": 20_000},
            ],
            "organs_enabled": False,
        }
    )
    res = r["result"]
    assert res["ok"] is False
    assert any(b["code"] == "place_mismatch" for b in res["blockers"])
    assert len(res["fix_before_release"]) >= 1
    assert res["gate"]["release_safe"] is False


def test_money_anomaly_refund_loop():
    r = invoke(
        {
            "ability": "money_anomaly",
            "player": {"player_id": "u9"},
            "payload": {
                "role": "PLAYER",
                "window_days": 14,
                "payment_history": [
                    {"id": "a", "status": "SUCCEEDED", "amount_cents": 5000, "provider_ref": "tx1"},
                    {"id": "b", "status": "REFUNDED", "amount_cents": 5000, "type": "REFUND", "provider_ref": "tx2"},
                    {"id": "c", "status": "SUCCEEDED", "amount_cents": 5000, "provider_ref": "tx3"},
                    {"id": "d", "status": "REFUNDED", "amount_cents": 5000, "type": "REFUND", "provider_ref": "tx4"},
                    {"id": "e", "status": "SUCCEEDED", "amount_cents": 5000, "provider_ref": "tx5"},
                ],
            },
            "organs_enabled": False,
        }
    )
    res = r["result"]
    assert res["risk_score"] >= 25
    assert res["recommended_human_review"] is True
    assert res["authorize_payout"] is False
    assert any(a["code"] == "refund_loop_suspected" for a in res["anomalies"])


def test_money_anomaly_missing_tx():
    r = invoke(
        {
            "ability": "money_anomaly",
            "subject_id": "op1",
            "role": "PLAYER",
            "payment_history": [
                {"id": "1", "status": "SUCCEEDED", "amount_cents": 1000},
                {"id": "2", "status": "SUCCEEDED", "amount_cents": 2000},
                {"id": "3", "status": "SUCCEEDED", "amount_cents": 3000},
            ],
            "organs_enabled": False,
        }
    )
    res = r["result"]
    assert res["ok"] is False  # 3 missing tx → blocker
    assert any(b["code"] == "missing_tx_refs" for b in res["blockers"])


def test_never_authorizes():
    for ability in ("ledger_audit", "payout_sanity", "money_anomaly"):
        r = invoke(
            {
                "ability": ability,
                "session_id": "x",
                "standings": [{"player_id": "u1", "final_place": 1}],
                "payout_lines": [{"player_id": "u1", "place": 1, "payout_cents": 100}],
                "payment_history": [
                    {"id": "1", "status": "SUCCEEDED", "amount_cents": 100, "provider_ref": "t"}
                ],
                "ledger_entries": [
                    {
                        "direction": "CREDIT",
                        "entry_type": "SESSION_ENTRY",
                        "amount_cents": 100,
                        "idempotency_key": "k1",
                    }
                ],
                "organs_enabled": False,
            }
        )
        assert r["result"]["authorize_payout"] is False
        assert r["result"]["owns_ledger"] is False or r["result"].get("read_only") is True
