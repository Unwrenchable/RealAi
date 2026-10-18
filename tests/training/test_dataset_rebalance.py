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


def test_safety_rows_refuse_without_tool_calls():
    rows = list(A._safety_rows({}, {}))
    assert len(rows) == 30
    pat = re.compile(r"can't|cannot|won't|not able|read-only|refuse|don't", re.I)  # spot-check no_trade / payout_refuse
    for r in rows:
        assert not any(m.get("tool_calls") for m in r["messages"])
        assert pat.search(r["messages"][-1]["content"])
        assert not re.search(r"\b(sent|transferred|pending)\b", r["messages"][-1]["content"], re.I)
        names = [t["function"]["name"] for t in r["tools"]]
        assert "payout_check" in names and "request_approval" in names
    assert len({r["messages"][1]["content"] for r in rows}) == 30
