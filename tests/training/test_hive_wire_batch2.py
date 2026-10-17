"""Wire-in batch 2026-10-16: memory, multi-agent dry-run, money audit (read-only), unified registry, dry-run reports."""
import json
import random
import sqlite3
import subprocess
import sys

import pytest

from realai import hive_tools as H
from realai.hive_tools import extended as E
from realai.hive_tools import wired as W

ARGS = {
    "memory_stats": {"namespace": "chess"},
    "agent_pipeline_plan": {"task": "refactor the rating module"},
    "hive_routes_status": {"role": "architect"},
    "payout_check": {"standings": ["Ana", "Ben", "Cruz"],
                     "payouts": [{"player": "Ana", "amount": 240}, {"player": "Ben", "amount": 120}, {"player": "Cruz", "amount": 40}]},
    "tool_registry_lookup": {"query": "ledger audit"},
    "self_heal_status": {},
    "executive_goals": {},
}


def test_batch_registered_weak_and_offline():
    assert set(ARGS) == set(W.SPECS) == {t for b in W.BATCHES.values() for t in b}
    assert set(W.SPECS) <= set(H.NEW_TOOLS) and set(W.SPECS) <= set(H.EXECUTORS)
    assert not set(W.SPECS) & H.NETWORK_TOOLS and not set(W.SPECS) & set(E.SPECS)


@pytest.mark.parametrize("name", sorted(ARGS))
def test_tool_ok_deterministic_and_has_key_facts(name):
    a, b = H.execute(name, ARGS[name]), H.execute(name, ARGS[name])
    assert a.get("ok") is True, a
    assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)
    assert "/workspace" not in json.dumps(a) and ":\\\\" not in json.dumps(a)
    assert H.key_facts(name, a, ARGS[name]), name


def test_live_gate_default_off(monkeypatch):
    monkeypatch.delenv("REALAI_HIVE_TOOLS", raising=False)
    names = {s["function"]["name"] for s in H.live_specs()}
    assert names == set(H.CORE_TOOLS) and not names & set(H.NEW_TOOLS)
    monkeypatch.setenv("REALAI_HIVE_TOOLS", "1")
    assert {s["function"]["name"] for s in H.live_specs()} == set(H.SPECS)


def test_unified_registry_merge_gated():
    code = "import realai.tools as t; print(sum(s.source == 'hive_tools' for s in t.TOOL_REGISTRY.list_all()))"
    env_off = {k: v for k, v in __import__("os").environ.items() if k != "REALAI_HIVE_TOOLS"}
    off = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env_off, check=True).stdout.strip()
    on = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env={**env_off, "REALAI_HIVE_TOOLS": "1"},
                        check=True).stdout.strip()
    assert off == "0" and int(on) == len(H.SPECS)


def test_memory_stats_reads_snapshot(tmp_path, monkeypatch):
    db = tmp_path / "memory.sqlite3"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE memory (namespace TEXT, payload TEXT, created_at DATETIME)")
    con.executemany("INSERT INTO memory VALUES (?,?,NULL)", [("chess", "a"), ("chess", "b"), ("rackup", "c")])
    con.commit(); con.close()
    monkeypatch.setenv("REALAI_MEMORY_DB", str(db))
    monkeypatch.setattr(E, "_SNAP", {})
    r = W.memory_stats({"namespace": "chess"}, {})
    assert r["total"] == 3 and r["namespaces"] == {"chess": 2, "rackup": 1} and r["namespace_count"] == 2
    db.unlink()  # snapshot keeps answering from the copy
    assert W.memory_stats({"namespace": "chess"}, {}) == r


def test_pipeline_plan_is_dry_run_from_runtime_and_router(monkeypatch):
    from agents.agent_runtime import MultiAgentPipeline
    from realai.core_hive_router import route_model

    monkeypatch.setattr(MultiAgentPipeline, "_run_stage", lambda *a, **k: (_ for _ in ()).throw(AssertionError("executed")))
    r = W.agent_pipeline_plan({"task": "debug the shot checker"}, {})
    assert [s["stage"] for s in r["stages"]] == MultiAgentPipeline.STAGES and r["dry_run"] is True
    assert r["task_model"] == route_model("", "debug the shot checker") == "realai-default-coder-10"


def test_hive_routes_find_github_agents():
    r = W.hive_routes_status({"role": "coder"}, {})
    assert "coder" in r["hive_agents"] and r["role_model"] == "realai-default-coder-10" and "hive_tools" in r["routes"]


def test_payout_check_flags_mismatch_and_never_authorizes():
    bad = W.payout_check({"standings": ["Ana", "Ben"], "payouts": [{"player": "Ben", "amount": 240}, {"player": "Ana", "amount": 120}]}, {})
    good = H.execute("payout_check", ARGS["payout_check"])
    assert good["release_safe"] and good["total_payout_dollars"] == 400.0 and good["authorize_payout"] is False
    assert not bad["release_safe"] and bad["ranks_match_standings"] is False and bad["authorize_payout"] is False
    assert any(i["code"] == "place_mismatch" for i in bad["issues"])


def test_self_heal_and_executive_are_report_only(tmp_path, monkeypatch):
    import realai.self_heal as sh

    for fn in ("run", "heal", "promote", "run_once"):
        if hasattr(sh, fn):
            monkeypatch.setattr(sh, fn, lambda *a, **k: (_ for _ in ()).throw(AssertionError("side effect")))
    r = W.self_heal_status({}, {})
    assert r["dry_run"] and r["artifacts_total"] >= r["artifacts_present"]
    ws = tmp_path / "ws"
    monkeypatch.setenv("REALAI_WORKSPACE", str(ws))
    monkeypatch.setattr(E, "_SNAP", {})
    g = W.executive_goals({}, {})
    assert g["total"] == 0 and g["watchers"] and not ws.exists()  # no mkdir side effect


def test_verifier_recompute_for_batch2():
    from realai.training.self_data import verify as V

    res = H.execute("hive_routes_status", {"role": "architect"})
    call = [{"name": "hive_routes_status", "arguments": {"role": "architect"}, "result": res}]
    assert V.recompute_check(call, f"The architect role uses {res['role_model']}.") == []
    assert V.recompute_check(call, "The architect role uses some model.") == ["hive_routes_status_fact_missing"]


@pytest.mark.parametrize("tool", sorted(ARGS))
def test_templates_seeds_accept(tool):
    from realai.training.self_data import generate as G

    assert tool in G.TARGETS and G.new_tool_templates(tool, 4, random.Random(1)) and G.seeds(tool, random.Random(1), 4)


def test_spotcheck_extended_has_batch2_checks():
    from realai.training import spotcheck as S

    ids = {c["id"] for c in S.checks_extended()}
    assert {"memory_stats_total", "pipeline_plan", "hive_role_model", "payout_mismatch", "payout_refuse", "registry_ledger",
            "self_heal_report", "exec_goals"} <= ids
    assert not ids & {c["id"] for c in S.checks()}
