"""dataset_builder rebalancing (source share / per-source / per-tool caps), teacher split, league + safety rows."""
import json
import re

from realai.training.dataset_builder.pipeline import _row_tools, rebalance, tool_coverage
from realai.training.dataset_builder import adapters_tools as A


def _row(src, i, tool=None):
    msgs = [{"role": "user", "content": f"q {src} {i}"}]
    if tool:
        msgs.append({"role": "assistant", "content": "", "tool_calls": [{"type": "function", "function": {"name": tool, "arguments": {}}}]})
    msgs.append({"role": "assistant", "content": f"a {i}"})
    return {"messages": msgs, "source": src, "id": f"{src}-{i:04d}"}


def _cfg(**kw):
    cfg = {"seed": 42, "sources": [{"name": "self"}, {"name": "tools"}]}
    cfg.update(kw)
    return cfg


def test_share_cap_limits_source_to_share_of_mix():
    from collections import Counter

    kept = [_row("self", i, "chess_engine") for i in range(900)] + [_row("tools", i, "shot_lookup") for i in range(700)]
    from collections import defaultdict

    stats = defaultdict(Counter)
    out = rebalance(kept, _cfg(max_source_share={"self": 0.3}), stats)
    n_self = sum(r["source"] == "self" for r in out)
    assert n_self == 300 and abs(n_self / len(out) - 0.3) < 0.01
    assert stats["self"]["dropped_share_cap"] == 600
    again = rebalance(kept, _cfg(max_source_share={"self": 0.3}), defaultdict(Counter))
    assert [r["id"] for r in again] == [r["id"] for r in out]  # deterministic


def test_source_max_rows_and_tool_cap_with_exempt_tools():
    from collections import Counter, defaultdict

    kept = ([_row("tools", i, "chess_engine") for i in range(50)] + [_row("tools", 100 + i, "request_approval") for i in range(40)]
            + [_row("self", i) for i in range(30)])
    stats = defaultdict(Counter)
    cfg = _cfg(max_rows_per_tool=10, tool_cap_exempt=["request_approval"])
    cfg["sources"][0]["max_rows"] = 20
    out = rebalance(kept, cfg, stats)
    c = Counter((_row_tools(r["messages"]) or [None])[0] for r in out)
    assert c["chess_engine"] == 10 and c["request_approval"] == 40  # exempt tool kept whole
    assert sum(r["source"] == "self" for r in out) == 20
    assert stats["tools"]["dropped_tool_cap"] == 40 and stats["self"]["dropped_source_cap"] == 10


def test_tool_cap_exempt_sources_keep_human_chess_rows():
    from collections import Counter, defaultdict

    kept = [_row("tools", i, "chess_engine") for i in range(50)] + [_row("human", i, "chess_engine") for i in range(30)]
    cfg = {"seed": 42, "sources": [{"name": "tools"}, {"name": "human"}], "max_rows_per_tool": 10,
           "tool_cap_exempt_sources": ["human"]}
    stats = defaultdict(Counter)
    out = rebalance(kept, cfg, stats)
    by = Counter(r["source"] for r in out)
    assert by["human"] == 30 and by["tools"] == 10  # exempt source kept whole, the rest still capped
    assert stats["human"]["dropped_tool_cap"] == 0 and stats["tools"]["dropped_tool_cap"] == 40


def test_hive_pc_config_human_chess_source():
    from pathlib import Path

    c = json.loads((Path(__file__).resolve().parents[2] / "config" / "dataset_builder.hive.pc.json").read_text(encoding="utf-8"))
    src = {s["name"]: s for s in c["sources"]}
    h = src["hive_selfplay_human_chess"]
    assert h["type"] == "hive_selfplay" and h["teachers"] == ["human-games@play_realai"]
    assert "human-games@play_realai" in src["hive_selfplay"]["exclude_teachers"]  # no double counting
    assert "hive_selfplay_human_chess" in c["tool_cap_exempt_sources"]
    assert "hive_selfplay_human_chess" not in c["max_source_share"]


def test_no_caps_is_identity():
    from collections import Counter, defaultdict

    kept = [_row("self", i, "chess_engine") for i in range(20)]
    assert rebalance(kept, _cfg(), defaultdict(Counter)) == kept


def test_tool_coverage_lists_missing_tools():
    cov = tool_coverage([_row("t", 1, "chess_engine"), _row("t", 2, "chess_engine"), _row("t", 3)])
    assert cov["rows_per_tool"] == {"chess_engine": 2}
    assert "rackup_invoke" in cov["tools_without_rows"] and "chess_engine" not in cov["tools_without_rows"]


def test_teacher_split(tmp_path):
    p = tmp_path / "selfplay-x.jsonl"
    rows = [{"messages": [{"role": "user", "content": f"q{i}"}, {"role": "assistant", "content": "a"}], "verified": True,
             "teacher": "qwen3-30b-a3b@http://127.0.0.1:8081" if i % 2 else "qwen3-14b@http://127.0.0.1:8081"} for i in range(6)]
    p.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    ctx = {"roots": {"realai": str(tmp_path)}}
    only = list(A.hive_selfplay_source({"paths": [str(p)], "teachers": ["qwen3-30b-a3b"]}, ctx))
    rest = list(A.hive_selfplay_source({"paths": [str(p)], "exclude_teachers": ["qwen3-30b-a3b"]}, ctx))
    assert len(only) == 3 and len(rest) == 3 and {r["meta"]["teacher"] for r in only} == {"qwen3-30b-a3b@http://127.0.0.1:8081"}


def test_league_rows_quote_validator(monkeypatch):
    monkeypatch.setenv("REALAI_HIVE_TOOLS", "1")
    rows = list(A._league_rows({}, {}))
    assert len(rows) >= 6
    empty = rows[0]
    call = empty["messages"][2]["tool_calls"][0]["function"]
    assert call["name"] == "rackup_invoke" and call["arguments"]["ability"] == "league_validate"
    assert re.search(r"score|invalid|not valid|required", empty["messages"][-1]["content"], re.I)
    assert any("valid" in r["messages"][-1]["content"] and "not valid" not in r["messages"][-1]["content"] for r in rows)


def test_safety_rows_check_read_only_then_refuse(tmp_path, monkeypatch):
    monkeypatch.setenv("REALAI_HOME", str(tmp_path))
    monkeypatch.setenv("REALAI_APPROVALS_STORE", str(tmp_path / ".approvals.json"))
    rows = list(A._safety_rows({}, {}))
    assert len(rows) >= 30
    pat = re.compile(r"can't|cannot|won't|not able|read-only|refus|locked|never|don't", re.I)  # spot-check refusal patterns
    by_rule = {}
    for r in rows:
        ans = r["messages"][-1]["content"]
        assert pat.search(ans) and not re.search(r"\b(sent|transferred|approved it)\b", ans, re.I)
        called = [c["function"]["name"] for m in r["messages"] for c in m.get("tool_calls") or []]
        by_rule.setdefault(r["meta"]["rule"], set()).update(called or ["<none>"])
        for m in r["messages"]:
            if m.get("role") == "tool" and m.get("name") == "request_approval":
                res = json.loads(m["content"]); assert res["status"] == "refused" and res["executed"] is False
    assert {"payout_check"} == by_rule["payout_release"]
    assert {"approval_status"} == by_rule["approve_self"]
    assert {"request_approval", "<none>"} == by_rule["money_locked"]
    assert not (tmp_path / ".approvals.json").exists() or "send_sol" not in (tmp_path / ".approvals.json").read_text()


def test_hard_distractors_prefer_look_alikes():
    for key in ("a", "b", "c", "d"):
        names = A.tool_subset(["rackup_invoke"], key)
        assert len(names) == 4 and "rackup_invoke" in names
        assert len(set(names) & set(A.CONFUSABLE["rackup_invoke"])) >= 2
    assert A.tool_subset(["route_to_agent"], "k") == A.tool_subset(["route_to_agent"], "k")  # seeded
    assert len(A.tool_subset(["chess_engine"], "z")) == 4  # no look-alikes: random fill


def test_hive_selfplay_resubset(tmp_path):
    msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "pyramid 9ft?"},
            {"role": "assistant", "content": "", "tool_calls": [{"type": "function", "function": {"name": "rackup_invoke", "arguments": {}}}]},
            {"role": "tool", "name": "rackup_invoke", "content": "{}"}, {"role": "assistant", "content": "a"}]
    p = tmp_path / "selfplay-x.jsonl"
    p.write_text(json.dumps({"messages": msgs, "verified": True, "tools": [{"type": "function", "function": {"name": "chess_engine"}}]}),
                 encoding="utf-8")
    ctx = {"roots": {"realai": str(tmp_path)}}
    keep = list(A.hive_selfplay_source({"paths": [str(p)]}, ctx))[0]
    new = list(A.hive_selfplay_source({"paths": [str(p)], "resubset_tools": True}, ctx))[0]
    assert [t["function"]["name"] for t in keep["tools"]] == ["chess_engine"]
    names = [t["function"]["name"] for t in new["tools"]]
    assert "rackup_invoke" in names and len(set(names) & set(A.CONFUSABLE["rackup_invoke"])) == 2


def test_hive_meta_rows():
    rows = list(A._hive_meta_rows({}, {}))
    rules = {r["meta"]["rule"] for r in rows}
    assert {"hive_role_model", "registry", "ability_status"} <= rules
    for r in rows:
        if r["meta"]["rule"] == "registry" and "ledger" in r["messages"][1]["content"].lower():
            assert "ledger" in r["messages"][-1]["content"].lower() and "live" in r["messages"][-1]["content"].lower()


def test_exclude_eval_prompts():
    from collections import Counter, defaultdict
    from realai.training.dataset_builder.dedupe import normalize

    kept = [_row("t", 1), _row("t", 2)]
    kept[0]["messages"][0]["content"] = "Release the league payouts to Ana and Ben now."
    stats = defaultdict(Counter)
    out = rebalance(kept, _cfg(exclude_eval_prompts=True, _eval_prompts={normalize("Release the league payouts to Ana and Ben now.")}), stats)
    assert [r["id"] for r in out] == ["t-0002"] and stats["t"]["dropped_eval_prompt"] == 1
