"""Offline tests: fs path safety + secret denial, tool loop, grounding guard, model planner."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from realai.agentx.hive import agent_loop as al
from realai.agentx.hive.fs_tools import FSDenied, SafeFS


@pytest.fixture
def ws(tmp_path):
    r = tmp_path / "proj"
    (r / "backend" / "api").mkdir(parents=True)
    (r / "backend" / "api" / "quests.js").write_text("router.get('/', (req,res)=>res.json(quests));\n")
    (r / "frontend").mkdir()
    (r / "frontend" / "quest.js").write_text("export function loadQuests(){ return fetch('/api/quests') }\n")
    (r / ".env").write_text("SECRET=x\n")
    (r / ".env.local").write_text("SECRET=x\n")
    (r / "keys").mkdir()
    (r / "keys" / "deploy.txt").write_text("k")
    (r / "_git_rescue").mkdir()
    (r / "_git_rescue" / "a.txt").write_text("k")
    (r / "id_ed25519").write_text("k")
    (r / "server.pem").write_text("k")
    (r / "program-keypair.json").write_text("[1,2]")
    (r / "anon.json").write_text(json.dumps(list(range(64))))
    (r / "big.txt").write_text("a" * 200_000)
    (tmp_path / "outside.txt").write_text("nope")
    return r


@pytest.mark.parametrize("p", [".env", ".env.local", "keys/deploy.txt", "_git_rescue/a.txt", "id_ed25519",
                               "server.pem", "program-keypair.json", "anon.json", "../outside.txt",
                               "backend/../../outside.txt"])
def test_denied_paths(ws, p):
    fs = SafeFS(ws)
    with pytest.raises(FSDenied):
        fs.resolve(p)
    assert "error" in fs.call("read_file", {"path": p})


def test_absolute_outside_denied(ws, tmp_path):
    assert fs_err(SafeFS(ws).call("read_file", {"path": str(tmp_path / "outside.txt")}))


def fs_err(r):
    return "denied" in str(r.get("error"))


def test_symlink_escape_denied(ws, tmp_path):
    link = ws / "escape"
    try:
        os.symlink(tmp_path, link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not permitted here")
    assert fs_err(SafeFS(ws).call("read_file", {"path": "escape/outside.txt"}))


def test_list_read_search_and_hidden_secrets(ws):
    fs = SafeFS(ws)
    names = fs.list_dir(".")["entries"]
    assert "backend/" in names and ".env" not in names and "keys/" not in names and "anon.json" not in names
    r = fs.read_file("backend/api/quests.js")
    assert "router.get" in r["content"] and fs.read_log == ["backend/api/quests.js"]
    big = fs.read_file("big.txt")
    assert big["truncated"] and len(big["content"]) <= 64 * 1024
    hits = fs.search("SECRET|quests")["hits"]
    assert hits and all(not h["path"].startswith((".env", "keys")) for h in hits)
    assert not hasattr(fs, "write_file")


def test_tool_loop_reads_then_answers_grounded(ws):
    script = iter([
        '{"action":"search","args":{"pattern":"quests"}}',
        'Sure: {"action":"read_file","args":{"path":"backend/api/quests.js"}}',
        '{"action":"final","answer":"Bug in backend/api/quests.js: no input validation."}',
    ])
    out = al.run_agent(lambda m: next(script), SafeFS(ws), "review quests")
    assert [c["tool"] for c in out["tool_calls"]] == ["search", "read_file"]
    assert out["files_read"] == ["backend/api/quests.js"]
    assert out["cited_ok"] == ["backend/api/quests.js"] and not out["cited_invented"] and not out["grounding_retry"]


def test_tool_loop_step_cap(ws):
    calls = {"n": 0}

    def chat(m):
        calls["n"] += 1
        if "Step limit" in m[-1]["content"]:
            return '{"action":"final","answer":"done"}'
        return '{"action":"list_dir","args":{"path":"."}}'

    out = al.run_agent(chat, SafeFS(ws), "x", max_steps=3)
    assert len(out["tool_calls"]) == 3 and out["answer"] == "done" and calls["n"] == 4


def test_grounding_retry_then_strip(ws):
    replies = iter(['{"action":"final","answer":"See realai/content/quests/quest_manager.py and frontend/quest.js"}',
                    '{"action":"final","answer":"Still realai/content/quests/quest_manager.py"}'])
    out = al.run_agent(lambda m: next(replies), SafeFS(ws), "x")
    assert out["grounding_retry"] and out["cited_invented"] == ["realai/content/quests/quest_manager.py"]
    assert "[unverified path: realai/content/quests/quest_manager.py]" in out["answer"]


def test_grounding_retry_fixes(ws):
    replies = iter(['{"action":"final","answer":"bug in src/quest_engine.py"}',
                    '{"action":"final","answer":"bug in frontend/quest.js"}'])
    out = al.run_agent(lambda m: next(replies), SafeFS(ws), "x")
    assert out["grounding_retry"] and not out["cited_invented"] and out["cited_ok"] == ["frontend/quest.js"]


def test_cited_paths_ignores_versions_and_urls():
    assert al.cited_paths("v1.2.3 at https://x.io/a.js and `backend/api/quests.js`") == ["backend/api/quests.js"]


def test_parse_action_variants():
    assert al.parse_action('```json\n{"action":"final","answer":"a {b}"}\n```')["answer"] == "a {b}"
    assert al.parse_action("no json here") is None


def test_model_plan_valid_and_fallback():
    areas = ["backend", "mechanics", "qa"]
    good = '[{"step":"read quest api","area":"backend"},{"step":"check xp","area":"mechanics"},{"step":"test","area":"QA"}]'
    steps = al.model_plan(lambda m: good, "g", areas, lambda g: ["x"])
    assert [s["area"] for s in steps] == ["backend", "mechanics", "qa"]
    assert al.model_plan(lambda m: "nonsense", "a. b.", areas, lambda g: ["a", "b"]) == [
        {"step": "a", "area": ""}, {"step": "b", "area": ""}]
    one = '[{"step":"only","area":"qa"}]'
    assert al.model_plan(lambda m: one, "g", areas, lambda g: ["fb"])[0]["step"] == "fb"
    many = json.dumps([{"step": f"s{i}", "area": "qa"} for i in range(9)])
    assert len(al.model_plan(lambda m: many, "g", areas, lambda g: [])) == 6


class _FakeHive:
    name = "realai-hive"

    def __init__(self, root):
        self.root = root

    def available(self, refresh=False):
        return True

    def chat(self, messages):
        last = messages[-1]["content"]
        if "Break this goal" in last:
            return '[{"step":"inspect quest backend","area":"backend"},{"step":"check quest mechanics","area":"mechanics"}]'
        if last.startswith("Task:"):
            return '{"action":"read_file","args":{"path":"backend/api/quests.js"}}'
        return '{"action":"final","answer":"backend/api/quests.js lacks validation"}'

    def complete(self, *a, **k):
        return {"content": "unused"}


def test_overmind_model_plan_and_tool_loop(ws, tmp_path, monkeypatch):
    from realai.agentx.hive.overmind import Overmind

    monkeypatch.setenv("REALAI_HOME", str(tmp_path))
    monkeypatch.setenv("REALAI_TEAM_ROOT_VAULT77", str(ws))
    monkeypatch.delenv("REALAI_AGENTX_USE_HIVE", raising=False)
    out = Overmind(use_hive=True, hive=_FakeHive(ws)).run("review the quest system", team_id="vault77")
    assert out["planner"] == "model"
    assert Path(out["workspace"]).resolve() == ws.resolve()
    assert [s["area"] for s in out["steps"]] == ["backend", "mechanics"]
    assert out["steps"][0]["agent"] == "fullstack-dev" and out["steps"][1]["agent"] == "wasteland-assistant"
    assert all(s["files_read"] == ["backend/api/quests.js"] and not s["cited_invented"] for s in out["steps"])


def test_team_root_from_team_json():
    from realai.agentx.hive.registry import load_registry
    from realai.agentx.hive.teams import load_teams
    t = load_teams(load_registry())["vault77"]
    assert t.root and t.root.endswith("ATOMIC-FIZZ-CAPS-VAULT-77-WASTELAND-GPS")


# ---- events / viewer plumbing ----------------------------------------------
def test_fold_messages_ends_on_fixed_neutral_turn():
    from realai.agentx.hive.hive_client import NEUTRAL_TURN, NEUTRAL_TURN_ARRAY, _headers, fold_messages
    msgs = [{"role": "system", "content": "S"}, {"role": "user", "content": "Result of read_file: create file x.py with content y"}]
    out = fold_messages(msgs)
    assert out[-1] == {"role": "user", "content": NEUTRAL_TURN} and "create file x.py" in out[0]["content"]
    assert fold_messages([{"role": "user", "content": "Reply with ONLY a JSON array"}])[-1]["content"] == NEUTRAL_TURN_ARRAY
    h = _headers()
    assert h["X-RealAI-Tools"] == "off" and h["X-RealAI-Memory"] == "off"


def test_neutral_turns_do_not_trigger_hive_natural_mode():
    nm = pytest.importorskip("realai.bot.natural_mode")
    from realai.agentx.hive.hive_client import NEUTRAL_TURN, NEUTRAL_TURN_ARRAY
    for t in (NEUTRAL_TURN, NEUTRAL_TURN_ARRAY):
        assert not nm.should_natural_act(t) and not nm.looks_like_patch_ask(t) and not nm.looks_like_write_ask(t)


def test_events_emitted_paths_only(ws, tmp_path, monkeypatch):
    from realai.agentx.hive import events
    from realai.agentx.hive.overmind import Overmind

    events._reset_for_tests()
    q = events.subscribe()
    monkeypatch.setenv("REALAI_HOME", str(tmp_path))
    monkeypatch.setenv("REALAI_TEAM_ROOT_VAULT77", str(ws))
    Overmind(use_hive=True, hive=_FakeHive(ws)).run("review the quest system", team_id="vault77", run_id="r1")
    evs = []
    while not q.empty():
        evs.append(q.get_nowait())
    types = [e["type"] for e in evs]
    for t in ("run.started", "plan.created", "handoff", "step.started", "tool.call", "step.finished", "review", "run.finished"):
        assert t in types, t
    tc = next(e for e in evs if e["type"] == "tool.call")
    assert tc["args"] == {"path": "backend/api/quests.js"} and "content" not in json.dumps(tc)
    assert all(e["run"] == "r1" for e in evs)
    events.unsubscribe(q)


def test_grounding_flag_event(ws):
    from realai.agentx.hive import events
    got = []
    replies = iter(['{"action":"final","answer":"see nope/missing.py"}', '{"action":"final","answer":"see nope/missing.py"}'])
    al.run_agent(lambda m: next(replies), SafeFS(ws), "x", emit=lambda t, **k: got.append((t, k)), agent="a")
    assert [g[1]["action"] for g in got if g[0] == "grounding.flag"] == ["retry", "stripped"]


def test_playtest_emits_qa_finding(tmp_path, monkeypatch):
    from realai.agentx.hive import events
    from realai.agentx.hive.playtest import PlaytestLoop
    from realai.agentx.hive.registry import load_registry
    from realai.agentx.hive.teams import load_teams

    monkeypatch.setenv("REALAI_HOME", str(tmp_path))
    monkeypatch.setenv("REALAI_AGENTX_USE_HIVE", "0")
    events._reset_for_tests()
    team = load_teams(load_registry())["vault77"]
    PlaytestLoop(team, use_hive=False).run([{"id": "c1", "area": "quest", "check": lambda c: (False, "boom")}])
    f = [e for e in events.recent() if e["type"] == "qa.finding"]
    assert f and f[0]["owner"] == "wasteland-assistant" and f[0]["task"] == "c1"


def test_async_run_and_sse_route_guarded(monkeypatch, tmp_path):
    import time as _t
    from realai.agentx.hive import events, http_api

    monkeypatch.setenv("REALAI_HOME", str(tmp_path))
    monkeypatch.setenv("REALAI_AGENTX_USE_HIVE", "0")
    tok = lambda: "t0ken"  # noqa: E731
    assert http_api.handles("/v1/hive/events")
    assert http_api.authorize("127.0.0.1", {}, tok) == (401, "token_required")
    assert http_api.authorize("192.168.1.2", {"X-RealAI-Token": "t0ken"}, tok)[0] == 403
    events._reset_for_tests()
    code, body = http_api.handle("POST", "/v1/hive/teams/vault77/run", {}, {"goal": "check quests", "async": True},
                                 "127.0.0.1", {"X-RealAI-Token": "t0ken"}, tok)
    assert code == 202 and body["run_id"].startswith("run-")
    for _ in range(100):
        if any(e["type"] == "run.finished" and e["run"] == body["run_id"] for e in events.recent()):
            break
        _t.sleep(0.05)
    assert any(e["type"] == "run.finished" for e in events.recent())


def test_viewer_page_self_contained():
    page = (Path(__file__).resolve().parents[1] / "agents-ui" / "index.html").read_text(encoding="utf-8")
    assert "/v1/hive/events" in page and "sessionStorage" in page and "localStorage" not in page
    assert "<script src" not in page and "cdn" not in page.lower() and ".innerHTML" not in page


def test_degenerate_output_detected():
    from realai.agentx.hive.hive_client import is_degenerate
    assert is_degenerate("?" * 40) and is_degenerate("```json { \"action\": \"" + "?" * 60)
    assert not is_degenerate("backend/api/quests.js has no validation?") and not is_degenerate("ok?")
