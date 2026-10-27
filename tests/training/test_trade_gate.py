"""trade_execute approval action (PR B): preview from the trading CLI, caps / bot wallet / safety / kill switch at request
time, one-time ticket hand-off at execute time (TTL from the approval), money lock unchanged for everything else."""
import json
import shutil
import time

import pytest

from realai.core import approval_gate as G
from realai.hive_tools import trade as T


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("REALAI_APPROVALS_STORE", str(tmp_path / ".approvals.json"))
    monkeypatch.setenv("REALAI_APPROVALS_AUDIT", str(tmp_path / "audit.jsonl"))
    monkeypatch.setenv("REALAI_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("REALAI_TRADE_BACKEND", "sim")
    monkeypatch.setenv("REALAI_TRADE_MODE", "1")
    monkeypatch.setenv("REALAI_TRADE_KILL_FILE", str(tmp_path / "KILL"))
    return tmp_path


def _prop(amount=4, to="JUP", slip=None):
    return T.trade_propose({"from": "USDC", "to": to, "amount": amount, "slippage_bps": slip}, {"trade_backend": "sim"})["proposalId"]


def _approve(rid, age=1.0):
    data = json.loads(open(G.store_path()).read())
    for it in data["items"]:
        if it["id"] == rid:
            it.update(status="approved", decided_by="travis", decided_at=time.time() - age)
    G._save(data)


def test_pending_card_with_full_preview(env):
    r = G.request("trade_execute", {"proposal_id": _prop()}, reason="buy JUP")
    assert r["status"] == "pending" and not r["executed"]
    pv = r["preview"]
    assert pv["kind"] == "trade" and pv["preview_hash"] and 60 <= pv["ticket_ttl_s"] <= 120
    for k in ("amountIn", "usd", "slippageBps", "minOut", "route", "caps", "wallet"):
        assert k in pv["trade"]
    for word in ("slippage", "min-out", "caps", "wallet", "via"):
        assert word in pv["summary"]


@pytest.mark.parametrize("args,why", [
    ({"proposal_id": "prop_nothex!!!"}, "proposal_id"),
    ({"proposal_id": "prop_0123456789", "amount": 999}, "only proposal_id"),
    ({"proposal_id": "prop_0123456789"}, "no preview"),
])
def test_bad_requests_refused(env, args, why):
    r = G.request("trade_execute", args)
    assert r["status"] == "refused" and why in r["error"]


def test_caps_safety_slippage_refused(env):
    assert "cap" in G.request("trade_execute", {"proposal_id": _prop(50)})["error"]
    assert "safety" in G.request("trade_execute", {"proposal_id": _prop(3, to="BONK")})["error"]
    assert "slippage" in G.request("trade_execute", {"proposal_id": _prop(2, slip=900)})["error"]


def test_python_hard_cap_is_independent(env, monkeypatch):
    monkeypatch.setenv("REALAI_TRADE_MAX_USD", "2")
    assert "hard cap 2" in G.request("trade_execute", {"proposal_id": _prop(4)})["error"]


def test_trade_mode_off_and_kill_switch(env, monkeypatch):
    pid = _prop()
    monkeypatch.setenv("REALAI_TRADE_MODE", "0")
    assert "trade mode is off" in G.request("trade_execute", {"proposal_id": pid})["error"]
    monkeypatch.setenv("REALAI_TRADE_MODE", "1")
    (env / "KILL").write_text("{}")
    assert "kill switch" in G.request("trade_execute", {"proposal_id": pid})["error"]


def test_execute_needs_approval_and_fresh_ticket(env):
    r = G.request("trade_execute", {"proposal_id": _prop()})
    assert "not approved" in G.execute(r["approval_id"])["error"]
    _approve(r["approval_id"], age=500)
    assert "expired" in G.execute(r["approval_id"])["error"]


def test_execute_in_sim_never_sends(env):
    r = G.request("trade_execute", {"proposal_id": _prop()})
    _approve(r["approval_id"])
    out = G.execute(r["approval_id"])
    assert out["result"]["mode"] == "sim" and not out["ok"]
    assert "already executed" in G.execute(r["approval_id"])["error"]  # one-time


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_execute_hands_ticket_to_cli(env, monkeypatch):
    r = G.request("trade_execute", {"proposal_id": _prop()})
    _approve(r["approval_id"])
    stub = env / "realai.js"
    stub.write_text("console.log(JSON.stringify({ok:true, mode:'live', argv:process.argv.slice(2), "
                    "store:process.env.REALAI_APPROVALS_STORE, txHash:'sig'}));")
    monkeypatch.setenv("REALAI_TRADE_CLI", str(stub))
    monkeypatch.setenv("REALAI_TRADE_BACKEND", "cli")
    out = G.execute(r["approval_id"])
    assert out["ok"] and out["result"]["txHash"] == "sig"
    item = G.get(r["approval_id"])
    assert item["status"] == "executed"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_cli_argv_is_ticketed_live_execute(env, monkeypatch):
    r = G.request("trade_execute", {"proposal_id": _prop()})
    _approve(r["approval_id"])
    seen = env / "argv.json"
    stub = env / "realai.js"
    stub.write_text("require('fs').writeFileSync(%r, JSON.stringify({argv:process.argv.slice(2), store:process.env.REALAI_APPROVALS_STORE}));"
                    "console.log('{\"ok\":false,\"mode\":\"refused\",\"error\":\"stub\"}');" % str(seen))
    monkeypatch.setenv("REALAI_TRADE_CLI", str(stub))
    monkeypatch.setenv("REALAI_TRADE_BACKEND", "cli")
    G.execute(r["approval_id"])
    got = json.loads(seen.read_text())
    pid = G.get(r["approval_id"])["payload"]["args"]["proposal_id"]
    assert got["argv"] == ["trade", "execute", pid, "--live", "--realai-ticket", r["approval_id"], "--json"]
    assert got["store"] == str(G.store_path())


def test_money_lock_unchanged(env):
    for cmd in ("solana transfer 9xQe 2 --allow-unfunded-recipient", "spl-token transfer MINT 5 RECIP", "cat ~/.config/solana/id.json keypair"):
        assert G.request("run_terminal_command", {"command": cmd})["status"] == "refused"
    # Travis 2026-10-19: buy / swap commands stay PENDING (not refused); trade_execute is the structured path
    assert G.request("run_terminal_command", {"command": "python scalper_bot.py --buy BONK"})["status"] == "pending"
    assert "money_locked" in G.request("trade_execute", {"proposal_id": "prop_0123456789", "reason": "send_sol to friend"})["error"]
