"""Trade mode bridge (PR A): opt-in tools, read-only research, dry-run proposals, sim backend, CLI allowlist + redaction."""
import json
import os
import shutil
import subprocess

import pytest

from realai import hive_tools
from realai.hive_tools import trade as T

SIM = {"trade_backend": "sim"}


def test_off_by_default_and_not_in_catalog(monkeypatch):
    monkeypatch.delenv("REALAI_TRADE_TOOLS", raising=False)
    assert "trade_propose" not in hive_tools.SPECS and "trade_research" not in hive_tools.SPECS
    names = {s["function"]["name"] if "function" in s else s["name"] for s in hive_tools.live_specs()}
    assert not names & {"trade_propose", "trade_research"}
    monkeypatch.setenv("REALAI_TRADE_TOOLS", "1")
    names = {s["function"]["name"] if "function" in s else s["name"] for s in hive_tools.live_specs()}
    assert {"trade_propose", "trade_research"} <= names


def test_named_specs_can_pick_trade_tools():
    sp = hive_tools.specs(["trade_research", "request_approval"])
    assert len(sp) == 2


def test_offline_execute_uses_sim_never_cli(monkeypatch):
    monkeypatch.setenv("REALAI_TRADE_CLI", "/nonexistent/realai.js")
    r = hive_tools.execute("trade_research", {"op": "spot", "symbol": "SOL"}, offline=True)
    assert r["ok"] and r["source"] == "sim" and r["price"] == 150.0


def test_research_validation():
    assert not T.trade_research({"op": "spot", "symbol": "SOL; rm -rf /"}, SIM)["ok"]
    assert not T.trade_research({"op": "token_check", "mint": "not-a-mint"}, SIM)["ok"]
    assert not T.trade_research({"op": "send", "symbol": "SOL"}, SIM)["ok"]
    assert not T.trade_research({"op": "backtest", "strategy": "yolo", "symbol": "SOL"}, SIM)["ok"]


def test_research_argv_allowlist():
    assert T._research_argv("spot", {"symbol": "sol"}) == ["market", "spot", "SOL/USD", "--json"]
    assert T._research_argv("token_check", {"mint": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN"})[:2] == ["token", "check"]
    for op in T.OPS:
        try:
            argv = T._research_argv(op, {"symbol": "SOL", "mint": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN", "strategy": "dca"})
        except ValueError:
            continue
        assert argv[0] in ("market", "token", "scan", "health", "paper", "backtest", "trade")
        assert not {"--live", "--yes", "send", "swap", "execute", "--realai-ticket"} & set(argv)


def test_propose_preview_and_caps():
    ok = T.trade_propose({"from": "USDC", "to": "JUP", "amount": 4}, SIM)
    assert ok["ok"] and ok["proposalId"].startswith("prop_") and ok["preview"]["usd"] == 4.0 and not ok["problems"]
    pv = ok["preview"]
    for k in ("amountIn", "usd", "slippageBps", "minOut", "route", "caps", "safety"):
        assert k in pv
    assert T.trade_propose({"from": "USDC", "to": "JUP", "amount": 4}, SIM)["proposalId"] == ok["proposalId"]  # deterministic
    big = T.trade_propose({"from": "USDC", "to": "JUP", "amount": 50}, SIM)
    assert not big["ok"] and any("per-trade cap" in p for p in big["problems"])
    unsafe = T.trade_propose({"from": "USDC", "to": "BONK", "amount": 3}, SIM)
    assert any("safety" in p for p in unsafe["problems"])
    slip = T.trade_propose({"from": "USDC", "to": "JUP", "amount": 2, "slippage_bps": 900}, SIM)
    assert any("slippage" in p for p in slip["problems"])
    assert not T.trade_propose({"from": "USDC", "to": "JUP", "amount": -1}, SIM)["ok"]


def test_cli_missing():
    os.environ.pop("REALAI_TRADE_CLI", None)
    r = T.trade_research({"op": "health"}, {"trade_backend": "cli"})
    assert not r["ok"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_cli_backend_scrubs_env_and_redacts(tmp_path, monkeypatch):
    stub = tmp_path / "realai.js"
    stub.write_text("const k=Object.keys(process.env).filter(x=>/KEY|SECRET|TOKEN|PASSWORD/i.test(x));"
                    "console.log('log line first');"
                    "console.log(JSON.stringify({ok:true, argv:process.argv.slice(2), leaked:k, "
                    "note:'0x' + 'ab'.repeat(32)}));")
    monkeypatch.setenv("REALAI_TRADE_CLI", str(stub))
    monkeypatch.setenv("JUPITER_API_KEY", "should-not-pass")
    r = T.trade_research({"op": "spot", "symbol": "SOL"}, {"trade_backend": "cli"})
    assert r["ok"] and r["argv"] == ["market", "spot", "SOL/USD", "--json"] and r["leaked"] == []
    assert "ab" * 32 not in json.dumps(r)
    p = T.trade_propose({"from": "USDC", "to": "JUP", "amount": 3, "slippage_bps": 80}, {"trade_backend": "cli"})
    assert p["argv"][:2] == ["trade", "propose"] and "--realai" in p["argv"] and "--live" not in p["argv"]


def test_key_facts():
    r = T.trade_propose({"from": "USDC", "to": "JUP", "amount": 4}, SIM)
    f = hive_tools.key_facts("trade_propose", r, {})
    assert [r["proposalId"]] in f
