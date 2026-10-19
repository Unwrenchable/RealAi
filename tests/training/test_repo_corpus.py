"""repo_corpus adapter: tool-grounded rows from the repo mirror, money = refusal only, caps, hold-out by repo."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from realai.training.dataset_builder.adapters import ADAPTERS
from realai.training.dataset_builder.adapters_repo import MONEY_ASKS, cap_per_repo

FAKE_TOKEN = "ghp_" + "K3" * 18  # runtime-built github_token look-alike (not a credential)
ROOT = Path(__file__).resolve().parents[2]


def _w(p: Path, text: str):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


@pytest.fixture
def mirror(tmp_path, monkeypatch):
    m = tmp_path / "repo-mirror"
    _w(m / "RealAi" / "README.md", "# RealAI\n\nLocal-first hive mind.\n")
    for i in range(6):
        _w(m / "RealAi" / "realai" / f"mod{i}.py", f"import os\n\n\ndef helper_fn_{i}(x):\n    return x + {i}\n\n\nclass Thing{i}Box:\n    pass\n")
    _w(m / "Rack_em_up" / "README.md", "# RackUp\n\nPool league and rating app.\n")
    _w(m / "Rack_em_up" / "src" / "rating.ts", "export function glickoUpdate(r: number) {\n  return r;\n}\n\nexport class LeagueTable {}\n")
    _w(m / "Rack_em_up" / "src" / "keys.ts", f"export const token = '{FAKE_TOKEN}';\n")
    _w(m / "Rack_em_up" / ".env", f"API_KEY={FAKE_TOKEN}\n")
    _w(m / "FizzSwap" / "README.md", "# FizzSwap\n\nA small DEX.\n")
    _w(m / "FizzSwap" / "src" / "pool.ts", "export function quoteSwap(a: number) {\n  return a;\n}\n")
    _w(m / "BlueScreenHelp" / "README.md", "# BlueScreenHelp\n\nFix blue screens.\n")
    _w(m / "BlueScreenHelp" / "dump.py", "def parse_minidump(path):\n    return path\n")
    _w(m / "Token-scalper" / "scalper_bot.py", "def buy_token(x):\n    return x\n")
    _w(m / "LustLink" / "README.md", "# LustLink\n")
    (m / "repo_mirror_manifest.json").write_text(json.dumps({"repos": {"Rack_em_up": {"commit": "f" * 40, "blocked": ["src/keys.ts"]}}}))
    ws = tmp_path / "ws"
    _w(ws / "README.md", "# RealAI\n\nworkspace copy\n")
    monkeypatch.setenv("REALAI_REPO_MIRROR", str(m))
    monkeypatch.setenv("REALAI_WORKSPACE", str(ws))
    return m


def rows_for(mirror, **spec):
    return list(ADAPTERS["repo_corpus"]({"mirror": str(mirror), **spec}, {"roots": {}}))


def _calls(row):
    msgs = row["messages"]
    out = []
    for i, m in enumerate(msgs):
        for tc in m.get("tool_calls") or []:
            res = json.loads(msgs[i + 1]["content"])
            out.append({"name": tc["function"]["name"], "arguments": tc["function"]["arguments"], "result": res})
    return out


def test_rows_are_tool_grounded_and_verify(mirror):
    from realai.training.self_data.verify import verify

    rows = rows_for(mirror, per_repo_share=1.0)
    rules = Counter(r["meta"].get("rule") for r in rows)
    assert {"overview", "list", "locate", "read", "edit_gated", "repo_money_locked"} <= set(rules)
    for r in rows:
        calls = _calls(r)
        if r["meta"].get("rule") == "repo_money_locked":
            continue
        assert calls and {c["name"] for c in calls} <= {"repo_search", "request_approval"}
        if r["meta"]["rule"] == "edit_gated":
            assert all(c["result"]["executed"] is False for c in calls)
            continue
        ok, why = verify(r["messages"], calls)
        assert ok, (r["meta"], why, r["messages"][-1]["content"])
        assert "repo_search" in [t["function"]["name"] for t in r["tools"]] and len(r["tools"]) == 4


def test_no_secrets_no_excluded_repos(mirror):
    blob = json.dumps(rows_for(mirror, per_repo_share=1.0))
    assert FAKE_TOKEN not in blob and "LustLink" not in blob and "keys.ts" not in blob and "buy_token" not in blob


def test_money_repos_are_refusal_only(mirror):
    rows = rows_for(mirror, per_repo_share=1.0)
    money = [r for r in rows if r["meta"].get("rule") == "repo_money_locked"]
    assert len(money) == sum(len(v) for v in MONEY_ASKS.values())
    for r in money:
        names = [c["name"] for c in _calls(r)]
        assert "request_approval" not in names and set(names) <= {"repo_search"}
        assert "won't" in r["messages"][-1]["content"] and "never" in r["messages"][-1]["content"]
    ts = [r for r in rows if r["meta"].get("repo") == "Token-scalper"]
    assert ts and all(r["meta"]["rule"] == "repo_money_locked" for r in ts)
    for r in ts:
        for c in _calls(r):
            assert c["result"]["ok"] is False  # never opened


def test_edit_rows_gated(mirror):
    rows = {r["meta"]["repo"]: r for r in rows_for(mirror, per_repo_share=1.0) if r["meta"].get("rule") == "edit_gated"}
    real = _calls(rows["RealAi"])[0]["result"]
    assert real["status"] == "pending" and real["executed"] is False and "pending" in rows["RealAi"]["messages"][-1]["content"]
    rack = _calls(rows["Rack_em_up"])[0]["result"]
    assert rack["status"] == "refused" and rack["executed"] is False
    assert "nothing changed" in rows["Rack_em_up"]["messages"][-1]["content"]


def test_per_repo_cap(mirror):
    rows = rows_for(mirror)  # default per_repo_share 0.25
    capped = [r for r in rows if r["meta"].get("rule") != "repo_money_locked"]
    n = Counter(r["meta"]["repo"] for r in capped)
    assert max(n.values()) <= max(1, int(len(rows_for(mirror, per_repo_share=1.0)) * 0.25))
    fake = [{"messages": [{}, {"content": str(i)}], "meta": {"repo": "A" if i < 8 else "B"}} for i in range(10)]
    out = cap_per_repo(fake, 0.25)
    assert Counter(r["meta"]["repo"] for r in out) == {"A": 2, "B": 2}


def test_holdout_repo_goes_to_eval_only(mirror, tmp_path, monkeypatch):
    from realai.training.dataset_builder.pipeline import build

    monkeypatch.setenv("REALAI_HOME", str(tmp_path / "home"))
    rows = rows_for(mirror, per_repo_share=1.0)
    assert all(r["meta"].get("split") == "eval" for r in rows if r["meta"].get("repo") == "BlueScreenHelp")
    cfg = {"name": "t", "sources": [{"name": "repo_corpus", "type": "repo_corpus", "mirror": str(mirror), "per_repo_share": 1.0}],
           "max_tokens": 4000, "eval_fraction": 0.0, "_eval_prompts": set()}
    res = build(cfg, dry_run=True, today="2026-10-19")
    assert not any(r["meta"].get("repo") == "BlueScreenHelp" for r in res.train)
    assert not any("parse_minidump" in json.dumps(r["messages"]) or "Fix blue screens" in json.dumps(r["messages"]) for r in res.train)
    assert any(r["meta"].get("repo") == "BlueScreenHelp" for r in res.eval)
    assert res.manifest["totals"]["eval_holdout"] >= 3


def test_no_mirror_only_plain_refusals(monkeypatch, tmp_path):
    monkeypatch.setenv("REALAI_REPO_MIRROR", str(tmp_path / "none"))
    rows = list(ADAPTERS["repo_corpus"]({}, {"roots": {}}))
    assert rows and all(r["meta"]["rule"] == "repo_money_locked" and not _calls(r) for r in rows)


def test_pc_config_entry_off_and_capped():
    cfg = json.loads((ROOT / "config" / "dataset_builder.hive.pc.json").read_text(encoding="utf-8"))
    src = next(s for s in cfg["sources"] if s["type"] == "repo_corpus")
    assert src["enabled"] is False and src["per_repo_share"] == 0.25 and src["mirror"] == "{repo_mirror}"
    assert cfg["max_source_share"]["repo_corpus"] == 0.15 and cfg["roots"]["repo_mirror"].startswith("D:/ARCHIVE")


def test_empty_capped_source_does_not_loosen_other_caps():
    from collections import defaultdict

    from realai.training.dataset_builder.pipeline import rebalance

    kept = [{"source": "hive_selfplay", "id": f"h{i:03d}", "messages": [{"role": "user", "content": f"h{i}"}]} for i in range(100)]
    kept += [{"source": "other", "id": f"o{i:03d}", "messages": [{"role": "user", "content": f"o{i}"}]} for i in range(70)]
    base = {"seed": 1, "sources": []}
    a = rebalance(list(kept), {**base, "max_source_share": {"hive_selfplay": 0.3}}, defaultdict(Counter))
    b = rebalance(list(kept), {**base, "max_source_share": {"hive_selfplay": 0.3, "repo_corpus": 0.15}}, defaultdict(Counter))
    assert [r["id"] for r in a] == [r["id"] for r in b]
