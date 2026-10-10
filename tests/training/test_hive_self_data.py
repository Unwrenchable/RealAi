"""Hive routing data: tool registry, tool loop, verifier, capture, spot-check gate, self-knowledge (offline)."""
import json

import pytest

from realai import hive_tools as H
from realai.hive_tools import tool_loop as L
from realai.training.self_data import capture as C
from realai.training.self_data.verify import verify


def test_network_tools_refused_offline_and_unknown_tool():
    assert H.execute("web_search", {"query": "x"}, offline=True)["ok"] is False
    assert H.execute("solana_read", {"address": "x"}, offline=True)["ok"] is False
    assert H.execute("nope", {})["ok"] is False


def test_rackup_only_readonly_abilities():
    assert H.execute("rackup_invoke", {"ability": "payout_execute"})["ok"] is False
    r = H.execute("rackup_invoke", {"ability": "pyramid_rules", "payload": {"table_size": "9ft", "skill_level": "beginner"}})
    assert r["ok"] and r["result"]["config"]["points_to_win"] == 40


def test_route_to_agent_and_ability_lookup():
    a = H.agents()[0]
    r = H.execute("route_to_agent", {"agent": a["id"], "task": "t"})
    assert r["ok"] and r["handoff"]["agent"] == a["id"]
    assert H.execute("route_to_agent", {"agent": "no-such-agent", "task": "t"})["ok"] is False
    r = H.execute("ability_lookup", {"query": "rating convert"})
    assert r["matches"][0]["id"] == "rating_convert"


def test_parse_tool_calls_native_and_text():
    n = L.parse_tool_calls({"tool_calls": [{"function": {"name": "math_solver", "arguments": "{\"problem\": \"1+1\"}"}}]})
    t = L.parse_tool_calls({"content": "<tool_call>\n{\"name\": \"shot_lookup\", \"arguments\": {\"query\": \"x\"}}\n</tool_call>"})
    assert n[0]["arguments"] == {"problem": "1+1"} and t[0]["name"] == "shot_lookup"


def _fake_chat(script):
    it = iter(script)

    def chat(messages, tools):
        return next(it)
    return chat


def test_tool_loop_executes_and_answers():
    chat = _fake_chat([{"tool_calls": [{"function": {"name": "rackup_invoke", "arguments": {"ability": "pyramid_rules",
                                                    "payload": {"table_size": "7ft", "skill_level": "beginner"}}}}]},
                       {"content": "<think></think>Per pyramid_rules: first to 25 points."}])
    r = L.run(chat, [{"role": "user", "content": "pyramid 7ft beginner?"}], offline=True)
    assert r["calls"][0]["result"]["ok"] and r["answer"] == "Per pyramid_rules: first to 25 points."
    assert [m["role"] for m in r["messages"]] == ["user", "assistant", "tool", "assistant"]
    ok, why = verify(r["messages"], r["calls"])
    assert ok, why


def _chess_call():
    return {"name": "chess_engine", "arguments": {"fen": "f"}, "result": {"ok": True, "best_move_san": "Qxf7#", "best_move_uci": "h5f7",
                                                                       "eval": "mate in 1 for White", "pv_san": ["Qxf7#"]}}


def test_verifier_rejects_hallucinations():
    msgs = lambda a: [{"role": "user", "content": "best move?"}, {"role": "assistant", "content": a}]
    assert verify(msgs("Stockfish: Qxf7# (h5f7), mate in 1 for White."), [_chess_call()])[0]
    ok, why = verify(msgs("Play Qxg7# (e5g7), mate in 1."), [_chess_call()])
    assert not ok and "chess_best_move_missing" in why
    ok, why = verify(msgs("Qxf7#, then Nf3 wins, +4.5 pawns"), [_chess_call()])
    assert not ok and any(w.startswith("ungrounded_numbers") or w.startswith("chess_moves") for w in why)
    assert not verify(msgs("The answer is 42"), [])[0]  # no tool call -> rejected
    failed = [{"name": "chess_engine", "arguments": {}, "result": {"ok": False, "error": "x"}}]
    assert not verify(msgs("Best move is e4"), failed)[0]
    assert verify(msgs("The engine failed, so I can't say."), failed)[0]


def test_capture_off_by_default_and_redacts(tmp_path, monkeypatch):
    monkeypatch.setenv("REALAI_HOME", str(tmp_path))
    monkeypatch.delenv("REALAI_CAPTURE", raising=False)
    m = [{"role": "user", "content": "rackup pyramid help, mail me at bob@example.com"}, {"role": "assistant", "content": "ok"}]
    assert C.capture(m) is None
    monkeypatch.setenv("REALAI_CAPTURE", "1")
    p = C.capture(m + [{"role": "user", "content": "wallet 7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"}])
    row = json.loads(p.read_text().splitlines()[0])
    assert row["project"] == "rackup" and "<EMAIL>" in json.dumps(row) and "<WALLET>" in json.dumps(row)
    assert str(p).startswith(str(tmp_path))
    p2 = C.capture([{"role": "user", "content": "send 5 sol to my friend"}, {"role": "assistant", "content": "no"}], project="atomicfizz")
    assert json.loads(p2.read_text().splitlines()[-1])["replay"] is False
    assert C.capture([{"role": "user", "content": "here is my seed phrase abandon ..."}]) is None


def test_verify_traffic_skips_money(tmp_path, monkeypatch):
    from realai.training.self_data import generate as G

    monkeypatch.setenv("REALAI_HOME", str(tmp_path))
    monkeypatch.setenv("REALAI_CAPTURE", "1")
    good = [{"role": "user", "content": "chess best move?"}, {"role": "assistant", "content": "Stockfish: Qxf7# (h5f7), mate in 1 for White."}]
    C.capture(good, calls=[_chess_call()], project="chess")
    C.capture([{"role": "user", "content": "transfer 3 sol"}, {"role": "assistant", "content": "x"}], project="atomicfizz")
    s = G.verify_traffic()
    assert s["per_project"]["chess"]["accepted"] == 1 and s["per_project"]["atomicfizz"]["money_skipped"] == 1
    assert G.verify_traffic()["per_project"] == {}  # already seen


def test_tool_rows_and_self_knowledge_are_current():
    from realai.training.dataset_builder.adapters_tools import _pyramid_rows, self_knowledge_source

    rows = list(_pyramid_rows({}, {"roots": {}}))
    r = rows[0]
    assert r["messages"][2]["tool_calls"][0]["function"]["name"] == "rackup_invoke" and r["messages"][3]["role"] == "tool"
    assert any(t["function"]["name"] == "rackup_invoke" for t in r["tools"]) and len(r["tools"]) == 4
    assert verify(r["messages"], [{"name": "rackup_invoke", "arguments": {}, "result": json.loads(r["messages"][3]["content"])}])[0]
    sk = list(self_knowledge_source({}, {"roots": {}}))
    n_ab = len(H.abilities())
    assert sum(1 for x in sk if "ability and is it live" in x["messages"][1]["content"]) == n_ab


def test_train_encoding_keeps_tool_rows(tmp_path):
    from realai.training import train_sft as T

    class Tok:
        def apply_chat_template(self, msgs, tokenize=True, add_generation_prompt=False, tools=None):
            s = ("T" if tools else "") + "".join(f"<{m['role'][0]}>{m.get('content') or json.dumps(m.get('tool_calls'))}|" for m in msgs)
            return [ord(c) for c in s + ("<a>" if add_generation_prompt else "")]

    msgs = [{"role": "user", "content": "q"}, {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "x", "arguments": {}}}]},
            {"role": "tool", "content": "OUT"}, {"role": "assistant", "content": "A"}]
    ids, lab = T.encode_assistant_only(Tok(), msgs, 1024, tools=[{"x": 1}])
    text = "".join(chr(i) for i, l in zip(ids, lab) if l != -100)
    assert "OUT" not in text and "A" in text and "name" in text


def test_register_default_refused_without_spotcheck(tmp_path, monkeypatch, capsys):
    from realai.training import train_sft as T

    monkeypatch.setenv("REALAI_HOME", str(tmp_path))
    run = tmp_path / "runs" / "r"
    run.mkdir(parents=True)
    (run / "train_result.json").write_text(json.dumps({"dataset": {"dir": "d", "manifest_sha256": "h"}, "best_eval_loss": 1.0}))
    (run / "eval_report.json").write_text(json.dumps({"passed": True}))
    a = T.build_parser().parse_args(["register", "--dataset", "d", "--out", str(run), "--model-id", "m", "--default"])
    assert T.register(a, T.recipe_from(a)) == 2 and "REFUSED" in capsys.readouterr().out
    (tmp_path / "runs" / "spotcheck-1.json").write_text(json.dumps({"pass_rate": 0.9, "passed": 18, "n": 20}))
    assert T.register(a, T.recipe_from(a)) == 0
    cat = json.loads((tmp_path / "models" / "trained_catalog.json").read_text())
    assert cat["models"][0]["default"] is True and cat["models"][0]["spotcheck"]["pass_rate"] == 0.9


def test_spotcheck_harness_scores_routing(monkeypatch):
    from realai.training import spotcheck as S

    def chat(messages, tools):
        if tools and messages[-1]["role"] == "user" and "Pyramid" in messages[-1]["content"] and "9-foot" in messages[-1]["content"]:
            return {"tool_calls": [{"function": {"name": "rackup_invoke", "arguments": {"ability": "pyramid_rules",
                                                 "payload": {"table_size": "9ft", "skill_level": "beginner"}}}}]}
        if messages[-1]["role"] == "tool":
            return {"content": "First to 40 points."}
        return {"content": "I am Qwen from Alibaba."}

    rep = S.run(chat, only=["pyramid_points", "identity"], log=lambda m: None)
    by = {r["id"]: r["passed"] for r in rep["results"]}
    assert by == {"pyramid_points": True, "identity": False} and rep["pass_rate"] == 0.5


def test_improvement_plan_upweights_failures(tmp_path, monkeypatch):
    from realai.training.self_data import improve as I

    monkeypatch.setenv("REALAI_HOME", str(tmp_path))
    (tmp_path / "runs").mkdir()
    (tmp_path / "runs" / "spotcheck-1.json").write_text(json.dumps({"pass_rate": 0.5, "results": [
        {"id": "c", "ability": "chess_engine", "passed": False, "routed": False, "fact_ok": False, "answer": "e4"},
        {"id": "p", "ability": "rackup_invoke", "passed": True, "routed": True, "fact_ok": True, "answer": "40"}]}))
    rep = I.analyse()
    assert rep["plan"]["chess_engine"] > rep["plan"]["rackup_invoke"] and rep["weak"][0]["tool"] == "chess_engine"
    md = I.write_report(rep)
    assert md.is_file() and str(md).startswith(str(tmp_path)) and I.latest_plan()["chess_engine"] == rep["plan"]["chess_engine"]


def test_orchestrator_hook_off_by_default(monkeypatch):
    from realai.hive_tools import orchestrator_hook as O

    monkeypatch.delenv("REALAI_TOOL_LOOP", raising=False)
    assert O.maybe_tool_loop({"messages": [{"role": "user", "content": "hi"}]}, {}, "http://127.0.0.1:9") is None
    assert O.wants_tool_loop({}, {"x-realai-tool-loop": "1"})


def test_pipeline_keeps_tool_calls(tmp_path, monkeypatch):
    from realai.training.dataset_builder import build

    monkeypatch.setenv("REALAI_HOME", str(tmp_path))
    cfg = {"name": "t", "roots": {}, "sources": [{"name": "tool_calls", "type": "tool_calls", "kinds": ["pyramid", "abilities"], "near_dedupe": False}]}
    r = build(cfg, dry_run=True)
    row = r.train[0]
    assert row["tools"] and any(m.get("tool_calls") for m in row["messages"]) and r.manifest["kinds"]["tool_call"] == len(r.train) + len(r.eval)
    assert not (tmp_path / "datasets").exists()
