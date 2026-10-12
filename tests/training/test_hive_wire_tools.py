"""Wire-audit tools (2026-10-12): read-only, deterministic, verifier recomputes via the same executor."""
import json
import random
import sqlite3

import pytest

from realai import hive_tools as H
from realai.hive_tools import extended as E

ARGS = {
    "rating_update_preview": {"player_rating": 520, "opponent_rating": 600, "won": True},
    "matchmaking_suggest": {"player_rating": 540, "candidates": [{"id": "Ana", "rating": 700}, {"id": "Ben", "rating": 545}]},
    "rating_intel": {"player_rating": 600, "rating_history": [520, 550, 575, 600]},
    "game_rules": {"discipline": "9-ball"},
    "coach_drill": {"rating": 450, "discipline": "8-ball", "minutes": 30},
    "hall_context": {"table_size": "9ft", "skill_level": "pro"},
    "module_lookup": {"query": "organs"},
    "plugin_lookup": {"query": "rackup coach"},
    "plugin_registry_list": {},
    "organs_hive_status": {"category": "cognitive"},
    "memory_search": {"query": "chess"},
    "approval_status": {},
}


def test_every_new_tool_registered_with_args_and_skips_documented():
    assert set(ARGS) == set(H.NEW_TOOLS) and set(H.NEW_TOOLS) <= set(H.SPECS) and set(H.NEW_TOOLS) <= set(H.EXECUTORS)
    assert "knowledge_query" in E.SKIPPED and "knowledge_query" not in H.SPECS
    assert not set(H.NEW_TOOLS) & H.NETWORK_TOOLS


@pytest.mark.parametrize("name", sorted(ARGS))
def test_new_tool_ok_and_deterministic(name):
    a, b = H.execute(name, ARGS[name]), H.execute(name, ARGS[name])
    assert a.get("ok") is True, a
    assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)
    assert "/workspace" not in json.dumps(a) and ":\\\\" not in json.dumps(a)  # repo-relative paths only


def test_rackup_values_come_from_gold():
    from realai.plugins.rackup_coach import invoke

    r = H.execute("rating_update_preview", ARGS["rating_update_preview"])
    g = invoke({"ability": "rating_update", "player": {"id": "player", "rating": 520, "rd": 175.0},
                "payload": {"won": True, "opponent_rating": 600, "opponent_rd": 175.0}})["result"]
    assert r["rating_after"] == g["rating_after"] and r["delta"] == g["delta"]
    assert H.execute("matchmaking_suggest", ARGS["matchmaking_suggest"])["best"] == "Ben"
    assert H.execute("hall_context", ARGS["hall_context"])["points_to_win"] == 71
    assert H.execute("game_rules", {"discipline": "snooker"})["ok"] is False


def test_memory_and_approvals_read_a_snapshot_never_the_source(tmp_path, monkeypatch):
    db = tmp_path / "memory.sqlite3"
    from agent_tools.engine.memory import SQLiteMemoryAdapter

    SQLiteMemoryAdapter(db).append("default", {"text": "chess opening notes: Italian game"})
    before = db.read_bytes()
    store = tmp_path / "appr.json"
    store.write_text(json.dumps({"items": [{"id": "a1", "action": "send_sol", "status": "pending"},
                                           {"id": "a2", "action": "x", "status": "approved"}]}))
    monkeypatch.setenv("REALAI_MEMORY_DB", str(db))
    monkeypatch.setenv("REALAI_APPROVALS_STORE", str(store))
    monkeypatch.setattr(E, "_SNAP", {})
    m = H.execute("memory_search", {"query": "chess"})
    assert m["ok"] and m["hits"] and db.read_bytes() == before
    assert E._SNAP["memory"] != db and str(tmp_path) not in str(E._SNAP["memory"])
    a = H.execute("approval_status", {})
    assert a["total"] == 2 and a["by_status"] == {"pending": 1, "approved": 1} and a["items"][0]["id"] == "a1"
    assert json.loads(store.read_text())["items"][0]["status"] == "pending"  # untouched
    assert not hasattr(E, "approve") and "update_request" not in open(E.__file__, encoding="utf-8").read()


def test_route_to_agent_dry_run_uses_real_runtime_without_executing(monkeypatch):
    import realai.v3_runtime_bridge as br

    def boom(*a, **k):
        raise AssertionError("dry run must not execute the pipeline")

    monkeypatch.setattr(br, "run_multi_agent", boom, raising=False)
    a = H.agents()[0]
    r = H.execute("route_to_agent", {"agent": a["id"], "task": "write unit tests"})
    h = r["handoff"]
    assert r["ok"] and h["agent"] == a["id"] and h["status"] == "planned (dry run)"
    assert h["stages"] == ["planner", "researcher", "critic", "executor", "synthesizer"] and h["model"]
    from realai.orchestration.hive_router import run_cycle

    assert run_cycle("x", agent="coder", dry_run=True)["action"] == "dry_run"


def test_pipeline_stage_constant_matches_agent_runtime():
    from agents.agent_runtime import MultiAgentPipeline

    from realai.orchestration.hive_router import PIPELINE_STAGES

    assert list(PIPELINE_STAGES) == list(MultiAgentPipeline.STAGES)


def _msgs(q, name, args, res, ans):
    return ([{"role": "user", "content": q},
             {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": name, "arguments": args}}]},
             {"role": "tool", "content": H.tool_json(res)}, {"role": "assistant", "content": ans}],
            [{"name": name, "arguments": args, "result": res}])


def test_verifier_recomputes_and_requires_key_fact():
    from realai.training.self_data.verify import verify

    args = ARGS["rating_update_preview"]
    res = H.execute("rating_update_preview", args)
    good = f"Your new rating is {res['rating_after']:.2f} ({res['display_after']})."
    assert verify(*_msgs("I beat a 600, I'm 520", "rating_update_preview", args, res, good)) == (True, [])
    ok, why = verify(*_msgs("q", "rating_update_preview", args, res, "Nice win, your rating went up."))
    assert not ok and "rating_update_preview_fact_missing" in why
    forged = dict(res, rating_after=999.0)
    ok, why = verify(*_msgs("q", "rating_update_preview", args, forged, "New rating 999."))
    assert not ok and "recompute_mismatch:rating_update_preview" in why
    mm = H.execute("matchmaking_suggest", ARGS["matchmaking_suggest"])
    assert verify(*_msgs("q", "matchmaking_suggest", ARGS["matchmaking_suggest"], mm, "Best match: Ben."))[0]


@pytest.mark.parametrize("tool", sorted(ARGS))
def test_generate_templates_and_seeds_for_new_tools(tool):
    from realai.training.self_data import generate as G

    assert tool in G.TARGETS
    qs = G.fallback_questions(tool, 4, random.Random(1))
    assert qs and all(isinstance(q, str) and len(q) > 10 for q in qs)
    G.seeds(tool, random.Random(1), 3)  # must not raise


def test_improve_marks_new_tools_weak(tmp_path, monkeypatch):
    from realai.training.self_data import improve as I

    monkeypatch.setenv("REALAI_HOME", str(tmp_path))
    rep = I.analyse()
    weak = {w["tool"] for w in rep["weak"] if w.get("new_tool")}
    assert weak == set(H.NEW_TOOLS)
    assert all(rep["plan"][t] >= I.NEW_TOOL_WEAK_WEIGHT > rep["plan"]["chess_engine"] for t in H.NEW_TOOLS)


def test_spotcheck_extended_suite_separate_from_core_gate(tmp_path, monkeypatch):
    from realai.training import ledger, spotcheck as S

    core = S.checks()
    ext = S.checks_extended()
    core16 = {"pyramid_points", "pyramid_7ft_pro", "rating_convert", "shot_route", "shot_tip", "chess_mate1", "chess_middlegame",
              "device_rec", "identity", "ability_status", "agent_security", "agent_accessibility", "math", "data_mean",
              "league_validate", "no_trade"}
    assert {c["id"] for c in core} <= core16  # core gate unchanged (shot/chess checks need their data/engine)
    tools_covered = {c["ability"] for c in ext}
    assert set(H.NEW_TOOLS) <= tools_covered
    assert sum(1 for c in ext if c["ability"] in H.NEW_TOOLS) <= 2 * len(H.NEW_TOOLS)
    rep = S.run(lambda m, t: {"content": "no"}, only=["organs_count"], log=lambda m: None, suite="extended")
    assert rep["suite"] == "extended" and rep["n"] == 1
    p = tmp_path / "r.json"
    p.write_text(json.dumps(rep))
    monkeypatch.setenv("REALAI_MODELS_LEDGER", str(tmp_path / "MODELS.md"))
    ledger.on_spotcheck(rep, p, "m1")
    sc = json.dumps(ledger.load())
    assert "tools_extended" in sc


def test_register_gate_ignores_extended_reports(tmp_path, monkeypatch, capsys):
    import time

    from realai.training import train_sft as T

    monkeypatch.setenv("REALAI_HOME", str(tmp_path))
    runs = tmp_path / "runs"
    runs.mkdir()
    (runs / "spotcheck-a.json").write_text(json.dumps({"pass_rate": 0.5, "suite": "core"}))
    time.sleep(0.02)
    (runs / "spotcheck-b.json").write_text(json.dumps({"pass_rate": 1.0, "suite": "extended"}))
    run = runs / "r"
    run.mkdir()
    (run / "train_result.json").write_text(json.dumps({"dataset": {"dir": "d", "manifest_sha256": "h"}, "best_eval_loss": 1.0}))
    (run / "eval_report.json").write_text(json.dumps({"passed": True}))
    a = T.build_parser().parse_args(["register", "--dataset", "d", "--out", str(run), "--model-id", "m", "--default"])
    assert T.register(a, T.recipe_from(a)) == 2 and "0.5" in capsys.readouterr().out


def test_verifier_smoke_regressions_2026_10_12():
    """Rejects from the first :8080 smoke that were verifier bugs, not model errors."""
    from realai.training.self_data.verify import verify

    a = ARGS["rating_intel"]
    r = H.execute("rating_intel", a)
    t = r["trajectory"].replace("_", " ").capitalize()
    assert verify(*_msgs("trend?", "rating_intel", a, r, f"Trajectory: {t}."))[0]
    ap = H.execute("approval_status", {})
    if ap["total"] == 0:
        assert verify(*_msgs("counts?", "approval_status", {}, ap,
                             "There are no approval requests; all counts are at zero."))[0]
    pl = H.execute("plugin_lookup", {"query": "public speaking coaching zz"})
    assert pl["ok"] is False
    assert verify(*_msgs("plugin?", "plugin_lookup", {"query": "public speaking coaching zz"}, pl,
                         "It seems there are no plugins for public speaking in the registry."))[0]
