"""self_data --seed-topics hook + filter v2 (incl. repo_search extension)."""
from __future__ import annotations

import json
import random
import subprocess
import sys

import pytest

from realai.training.self_data import filter as F
from realai.training.self_data import generate as G

SPOT_Q = "What's the mean and median of 4, 8, 15, 16, 23, 42?"  # a core spot-check question
FAKE_TOKEN = "ghp_" + "M4" * 18  # runtime-built github_token look-alike (not a credential)


def test_load_seed_topics_formats_and_eval_exclusion(tmp_path):
    from realai.training.dataset_builder.dedupe import normalize

    (tmp_path / "eco.json").write_text(json.dumps({"projects": [{"name": "RackUp", "summary": "pool league app"},
                                                                {"title": "Atomic Fizz Caps"}], "topics": ["Overseer bot", SPOT_Q]}))
    (tmp_path / "chunks.jsonl").write_text(json.dumps({"title": "Hive memory"}) + "\n" + json.dumps({"topic": "RackUp"}) + "\n")
    (tmp_path / "README.md").write_text("# RealAI\n\ntext\n## Approval gate\n")
    topics = G.load_seed_topics([str(tmp_path / n) for n in ("eco.json", "chunks.jsonl", "README.md", "missing.txt")],
                                exclude={normalize(SPOT_Q)})
    assert {"RackUp", "Atomic Fizz Caps", "Overseer bot", "Hive memory", "RealAI", "Approval gate"} <= set(topics)
    assert SPOT_Q not in topics and topics.count("RackUp") == 1
    f1 = G.topic_focus(topics, random.Random(1))
    assert f1 == G.topic_focus(topics, random.Random(1)) and "ecosystem topics" in f1 and G.topic_focus([], random.Random(1)) == ""


def test_run_uses_topics_and_skips_spotcheck_prompts(tmp_path, monkeypatch):
    monkeypatch.setenv("REALAI_HOME", str(tmp_path))
    prompts = []

    def chat(msgs, tools):
        if tools is None:  # proposer
            prompts.append(msgs[-1]["content"])
            return {"content": json.dumps([SPOT_Q, "Average of 3, 9, 12?"])}
        return {"content": "I don't know."}

    s = G.run(chat, plan={"data_analysis": 1}, minutes=0.003, max_rows=5, per_batch=2, seed=3, log=lambda m: None,
              seed_topics=["RackUp leagues", "Atomic Fizz Caps"])
    assert prompts and all("ecosystem topics" in p for p in prompts)
    assert s["per_tool"]["data_analysis"]["eval_prompt_skipped"] >= 1 and s["seed_topics"] == 2
    rej = (tmp_path / "datasets" / "_sources" / "hive_selfplay").glob("rejects-*.jsonl")
    assert all(SPOT_Q not in p.read_text() for p in rej)


def test_repo_search_is_a_selfplay_target():
    assert "repo_search" in G.TARGETS and G.ACCEPT_TOOLS["repo_search"] == {"repo_search"}
    assert "Travis's own repos" in G.seeds("repo_search", random.Random(0), 4)
    assert G.fallback_questions("repo_search", 3, random.Random(0))


def test_cli_has_seed_topics_and_filter():
    out = subprocess.run([sys.executable, "-m", "realai.training.self_data", "generate", "--help"], capture_output=True, text=True).stdout
    assert "--seed-topics" in out
    out = subprocess.run([sys.executable, "-m", "realai.training.self_data", "filter", "--help"], capture_output=True, text=True).stdout
    assert "--write" in out and "--recompute" in out


# ----------------------------------------------------------------------------- filter v2
def _row(q, calls, ans, tool="x", teacher="qwen3-30b-a3b@http://127.0.0.1:8080"):
    msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": q}]
    for name, args, res in calls:
        msgs.append({"role": "assistant", "content": "", "tool_calls": [{"type": "function", "function": {"name": name, "arguments": args}}]})
        msgs.append({"role": "tool", "name": name, "content": json.dumps(res)})
    msgs.append({"role": "assistant", "content": ans})
    return {"messages": msgs, "tool": tool, "teacher": teacher, "verified": True}


GREP = {"ok": True, "action": "grep", "query": "def f", "repo": "Rack_em_up",
        "hits": [{"repo": "Rack_em_up", "path": "src/rating.ts", "line": 3, "text": "export function f() {"}]}


@pytest.mark.parametrize("row,why", [
    (_row("q", [("math_solver", {"problem": "x"}, {"ok": False, "error": "bad"})], "The answer is 4."), "failed_tool"),
    (_row("APA 5?", [("rackup_invoke", {"ability": "rating_convert", "payload": {"from": "apa", "rating": 5}}, {"ok": True})], "500"),
     "rating_convert_keys"),
    (_row("pyr", [("rackup_invoke", {"ability": "pyramid_rules", "payload": {"table_size": "8ft", "skill_level": "pro"}}, {"ok": True})], "x"),
     "pyramid_rules_table_size"),
    (_row("where is f?", [("repo_search", {"action": "grep", "repo": "Rack_em_up", "query": "def f"}, GREP)],
          "It's in src/utils/helpers.ts."), "repo_search_ungrounded_path"),
    (_row("where is f?", [("repo_search", {"action": "grep", "repo": "Rack_em_up", "query": "def f"}, GREP)],
          f"src/rating.ts line 3; token {FAKE_TOKEN}"), "repo_search_secret"),
    (_row("where is f?", [("repo_search", {"action": "grep", "repo": "Rack_em_up", "query": "def f"}, GREP)],
          "src/rating.ts: <redacted:secret>"), "repo_search_secret"),
    (_row("LustLink readme?", [("repo_search", {"action": "read", "repo": "LustLink", "path": "README.md"},
                                {"ok": True, "action": "read", "path": "README.md", "lines": ["1: x"]})], "README.md says x"),
     "repo_search_excluded_repo"),
    (_row("Run my scalper bot", [("request_approval", {"action": "run_terminal_command", "command": "python scalper_bot.py --buy BONK"},
                                  {"ok": True, "status": "pending", "executed": False})], "Filed; pending approval."), "money_approval_filed"),
])
def test_filter_rejects(row, why):
    assert F.reject_reason(row) == why


def test_filter_keeps_grounded_and_guard_refusals():
    good = _row("where is f?", [("repo_search", {"action": "grep", "repo": "Rack_em_up", "query": "def f"}, GREP)],
                "`f` is defined in Rack_em_up:src/rating.ts:3.")
    guard = _row("Run Token-scalper", [("repo_search", {"action": "list", "repo": "Token-scalper"},
                                        {"ok": False, "error": "repo 'Token-scalper' is not in the searchable allowlist"})],
                 "I won't do that: RealAI never trades, and repo_search can't open Token-scalper.")
    git = _row("git status", [("request_approval", {"action": "run_terminal_command", "command": "git status"},
                               {"ok": True, "status": "pending", "executed": False})], "Pending approval.")
    for r in (good, guard, git):
        assert F.reject_reason(r) is None


def test_filter_files_report_then_write(tmp_path):
    d = tmp_path / "hive_selfplay"
    d.mkdir()
    bad = _row("q", [("math_solver", {}, {"ok": False})], "4")
    good = _row("where is f?", [("repo_search", {"action": "grep", "repo": "Rack_em_up", "query": "def f"}, GREP)],
                "Rack_em_up:src/rating.ts:3")
    p = d / "selfplay-20261019-0100.jsonl"
    body = json.dumps(good) + "\n" + json.dumps(bad) + "\n"
    p.write_text(body)
    other = d / "selfplay-other.jsonl"
    other.write_text(json.dumps(_row("q", [("math_solver", {}, {"ok": False})], "4", teacher="local@x")) + "\n")
    rep = F.filter_files([str(d / "selfplay-*.jsonl")], teacher_prefix="qwen3-30b-a3b")
    assert rep["files"] == {p.name: {"raw": 2, "kept": 1}} and p.read_text() == body  # report only
    rep = F.filter_files([str(p)], teacher_prefix="qwen3-30b-a3b", archive=str(tmp_path / "arch"), write=True)
    assert len(p.read_text().splitlines()) == 1 and (d / "selfplay-20261019-0100.jsonl.raw").read_text() == body
    assert (tmp_path / "arch" / p.name).read_text() == body
    p.write_text(body)
    F.filter_files([str(p)], write=True)
    assert (d / "selfplay-20261019-0100.jsonl.pre-v3").read_text() == body
    p.write_text(body)
    with pytest.raises(SystemExit):
        F.filter_files([str(p)], write=True)  # both raw slots used: refuse, never overwrite
    assert p.read_text() == body


def test_verify_rejects_ungrounded_repo_paths(tmp_path, monkeypatch):
    from realai.training.self_data.verify import verify

    m = tmp_path / "m" / "Rack_em_up" / "src"
    m.mkdir(parents=True)
    (m / "rating.ts").write_text("// x\n\nexport function glickoStep() {}\n")
    monkeypatch.setenv("REALAI_REPO_MIRROR", str(tmp_path / "m"))
    from realai import hive_tools as H

    args = {"action": "grep", "repo": "Rack_em_up", "query": "function glickoStep"}
    res = H.execute("repo_search", args)
    msgs = [{"role": "user", "content": "Where is glickoStep?"}, {"role": "assistant", "content": "In src/rating.ts, and also lib/glicko.ts."}]
    ok, why = verify(msgs, [{"name": "repo_search", "arguments": args, "result": res}])
    assert not ok and any(w.startswith("repo_search_ungrounded_path") for w in why)
    msgs[-1]["content"] = "`glickoStep` is in Rack_em_up:src/rating.ts:3."
    assert verify(msgs, [{"name": "repo_search", "arguments": args, "result": res}])[0]


def test_repo_corpus_skips_redacted_results(tmp_path, monkeypatch):
    from realai.training.dataset_builder.adapters import ADAPTERS

    m = tmp_path / "m" / "Rack_em_up"
    (m / "src").mkdir(parents=True)
    (m / "README.md").write_text("# RackUp\n\nLeague app.\n")
    (m / "src" / "cfg.ts").write_text("export function loadCfg() {\n  const apiKey = 'abcdefgh12345678';\n}\n")
    (m / "src" / "ok.ts").write_text("export function cleanFn() {\n  return 1;\n}\n")
    monkeypatch.setenv("REALAI_REPO_MIRROR", str(tmp_path / "m"))
    monkeypatch.setenv("REALAI_WORKSPACE", str(tmp_path))
    rows = list(ADAPTERS["repo_corpus"]({"per_repo_share": 1.0, "repos": ["Rack_em_up"]}, {"roots": {}}))
    blob = json.dumps(rows)
    assert "<redacted" not in blob and "abcdefgh12345678" not in blob
    assert any(r["meta"].get("rule") == "locate" for r in rows)
