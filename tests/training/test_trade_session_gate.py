"""trade_session approval action (AI auto trading): ONE card arms one bounded live-auto session of the CLI's AI mode.
Request-time hard caps, Solana / power only, kill switch, a preview hash the CLI re-checks (same canonical JSON as
core/realai-ticket.js), and execute() runs nothing and does not consume the card (the CLI arms it itself)."""
import hashlib
import json
import time

import pytest

from realai.core import approval_gate as G
from realai.hive_tools import approvals as A


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("REALAI_APPROVALS_STORE", str(tmp_path / ".approvals.json"))
    monkeypatch.setenv("REALAI_APPROVALS_AUDIT", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("REALAI_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("REALAI_TRADE_MODE", "1")
    monkeypatch.setenv("REALAI_TRADE_KILL_FILE", str(tmp_path / "KILL"))
    for k in ("REALAI_TRADE_MAX_USD", "REALAI_TRADE_MAX_SESSION_USD", "REALAI_TRADE_MAX_OPEN", "REALAI_TRADE_MAX_SESSION_HOURS"):
        monkeypatch.delenv(k, raising=False)
    return tmp_path


OK = {"per_trade_usd": 5, "budget_usd": 15, "max_open": 2, "hours": 4, "chain": "solana", "profile": "power"}


def _approve(rid, age=1.0):
    data = json.loads(open(G.store_path()).read())
    for it in data["items"]:
        if it["id"] == rid:
            it.update(status="approved", decided_by="travis", decided_at=time.time() - age)
    G._save(data)


def test_pending_session_card_with_hash_the_cli_can_check(env):
    r = G.request("trade_session", dict(OK), reason="AI auto trading this afternoon")
    assert r["status"] == "pending" and not r["executed"]
    pv = r["preview"]
    assert pv["kind"] == "trade_session" and pv["arm_ttl_s"] == 900
    s = pv["session"]
    assert s == {"v": 1, "kind": "trade_session", "perTradeUsd": 5, "budgetUsd": 15, "maxOpen": 2, "hours": 4, "chain": "solana",
                 "profile": "power"}
    assert pv["preview_hash"] == hashlib.sha256(G.canonical(s).encode()).hexdigest()
    for word in ("per entry", "total", "open", "same wallet", "never"):
        assert word in pv["summary"]
    assert "--realai-session" in pv["note"]


def test_canonical_matches_the_cli():
    # value printed by the Node CLI: hashPreview({v:1,kind:'trade_session',perTradeUsd:5,budgetUsd:12.5,maxOpen:2,hours:1.5,chain:'solana',profile:'power'})
    s = {"v": 1, "kind": "trade_session", "perTradeUsd": 5.0, "budgetUsd": 12.5, "maxOpen": 2, "hours": 1.5, "chain": "solana", "profile": "power"}
    assert G.canonical(s) == '{"budgetUsd":12.5,"chain":"solana","hours":1.5,"kind":"trade_session","maxOpen":2,"perTradeUsd":5,"profile":"power","v":1}'
    assert hashlib.sha256(G.canonical(s).encode()).hexdigest() == "567d147627c67eef38dea2c667d61dcea5ccbefbf697de0a3c951090348162ab"


@pytest.mark.parametrize("over,why", [
    ({"per_trade_usd": 6}, "hard cap 5"),
    ({"budget_usd": 50}, "hard cap 15"),
    ({"max_open": 4}, "max_open"),
    ({"max_open": 1.5}, "whole number"),
    ({"hours": 48}, "hard cap 24"),
    ({"budget_usd": 3}, ">= per_trade_usd"),
    ({"chain": "ethereum"}, "Solana only"),
    ({"profile": "balanced"}, "profile must be power"),
    ({"per_trade_usd": 0}, "> 0"),
    ({"hours": "lots"}, "must be a number"),
    ({"wallet": "../keys/bot.json"}, "configured NAME"),
    ({"to_address": "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin"}, "takes only"),
    ({"max_trade_usd": 500}, "takes only"),
])
def test_out_of_bounds_session_refused(env, over, why):
    r = G.request("trade_session", {**OK, **over})
    assert r["status"] == "refused" and why in r["error"], r


def test_mode_off_and_kill_switch_refuse(env, monkeypatch):
    (env / "KILL").write_text("x")
    assert "kill switch" in G.request("trade_session", dict(OK))["error"]
    (env / "KILL").unlink()
    monkeypatch.setenv("REALAI_TRADE_MODE", "0")
    assert "trade mode is off" in G.request("trade_session", dict(OK))["error"]


def test_hard_caps_are_env_tunable_down(env, monkeypatch):
    monkeypatch.setenv("REALAI_TRADE_MAX_USD", "2")
    assert "hard cap 2" in G.request("trade_session", dict(OK))["error"]


def test_execute_runs_nothing_and_does_not_consume(env):
    rid = G.request("trade_session", dict(OK))["approval_id"]
    assert G.execute(rid)["ok"] is False  # pending: refused like every gate action
    _approve(rid)
    r = G.execute(rid)
    assert r["ok"] and r["result"]["armed"] is False and rid in r["result"]["note"]
    it = G.get(rid)
    assert it["status"] == "approved" and not it.get("executed"), "the CLI consumes the card when it arms the session"
    _approve(rid, age=5000)
    r = G.execute(rid)
    assert not r["ok"] and "expired" in r["result"]["note"]


def test_request_approval_tool_offers_trade_session(env):
    spec = A.SPECS["request_approval"]
    params = spec["function"]["parameters"] if "function" in spec else spec["parameters"]
    assert "trade_session" in params["properties"]["action"]["enum"]
    for k in ("per_trade_usd", "budget_usd", "max_open", "hours", "chain", "profile"):
        assert k in params["properties"]
    r = A.request_approval({"action": "trade_session", "reason": "auto", **OK}, {"approvals_sandbox": True})
    assert r["status"] == "pending" and r["executed"] is False


def test_money_still_locked(env):
    r = G.request("trade_session", {**OK, "reason": "then transfer_sol to my other wallet"})
    assert r["status"] == "refused" and "money_locked" in r["error"]
