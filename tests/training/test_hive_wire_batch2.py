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


def test_payout_check_facts_skip_arg_error_and_accept_correctly_wording():
    """Smoke 2026-10-17 reject: first call failed arg validation (model retried with players); the answer said the
    payouts 'match the final standings correctly'. That is a verifier bug, not a model mistake."""
    from realai import hive_tools
    from realai.training.self_data.verify import recompute_check

    bad = {"standings": ["Alice", "Bob", "Charlie"], "payouts": [{"amount": 500}, {"amount": 300}, {"amount": 200}]}
    good = {"standings": ["Alice", "Bob", "Charlie"],
            "payouts": [{"player": "Alice", "amount": 500}, {"player": "Bob", "amount": 300}, {"player": "Charlie", "amount": 200}]}
    calls = [{"name": "payout_check", "arguments": a, "result": hive_tools.execute("payout_check", a, offline=True)} for a in (bad, good)]
    assert calls[0]["result"].get("ok") is False and calls[1]["result"]["release_safe"] is True
    ans = "The payout amounts match the final standings correctly. Total $1000; safe for RackUp to consider for release."
    assert recompute_check(calls, ans) == []
    assert recompute_check(calls[1:], "I could not tell.") == ["payout_check_fact_missing"]


def test_refused_request_reported_honestly_is_not_a_success_claim():
    """Smoke 2026-10-17 reject: request_approval was refused (old_string matched 8 times) and the answer said so."""
    from realai.training.self_data.verify import verify

    calls = [{"name": "request_approval", "arguments": {"action": "search_replace"},
              "result": {"ok": False, "status": "refused", "executed": False, "next_step": "not filed"}}]
    msgs = [{"role": "user", "content": "rename it"},
            {"role": "assistant", "content": "The request was refused because old_string matches 8 times."}]
    assert verify(msgs, calls) == (True, ["all_tools_failed"])
    msgs[-1]["content"] = "Done, the README now says SynthMind."
    assert verify(msgs, calls) == (False, ["all_tools_failed_but_answer_claims_success"])


def test_extract_questions_collects_several_single_element_arrays():
    """Smoke 2026-10-17: the 14B answered the payout_check proposal with three one-element arrays; only one was used."""
    from realai.training.self_data.generate import extract_questions

    t = '["Check payouts for Alice, Bob, Charlie: $500, $300, $200?"]\n\n["Sarah, Mike, Tom got $1000, $600, $400. Align?"]\n\n' \
        '["Order is Jordan, Lisa, Kevin; payouts $800, $450, $350. Consistent?"]'
    assert len(extract_questions(t)) == 3
    assert extract_questions('["first request here", "second request here"] trailing [1, 2]') == ["first request here", "second request here"]
