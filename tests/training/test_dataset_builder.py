"""Tests for realai.training.dataset_builder (offline, tmp REALAI_HOME)."""
from __future__ import annotations

import json
import os

import pytest

from realai.training.dataset_builder import build
from realai.training.dataset_builder.adapters import agent_md_pairs, row_to_messages, shot_pairs
from realai.training.dataset_builder.dedupe import NearDedupe, exact_key
from realai.training.dataset_builder.scrub import find_secrets, redact


@pytest.fixture
def home(tmp_path, monkeypatch):
    for k in list(os.environ):
        if k.startswith("REALAI_"):
            monkeypatch.delenv(k, raising=False)
    h = tmp_path / "home"
    h.mkdir()
    monkeypatch.setenv("REALAI_HOME", str(h))
    return h


def _write(path, rows):
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def _cfg(tmp_path, rows, **kw):
    src = _write(tmp_path / "src.jsonl", rows)
    cfg = {"name": "t", "min_tokens": 1, "sources": [{"name": "s", "type": "jsonl", "paths": [str(src)], "license": "own"}]}
    cfg.update(kw)
    return cfg


def _qa(q, a):
    return {"instruction": q, "response": a}


def test_row_formats():
    assert row_to_messages({"text": "### Instruction:\nhi\n\n### Response:\nyo"})[1]["content"] == "yo"
    assert row_to_messages({"text": "<|user|>\nq\n<|assistant|>\na"})[-1] == {"role": "assistant", "content": "a"}
    assert row_to_messages({"messages": [{"role": "user", "content": "q"}]}) is None
    assert row_to_messages({"text": "You are the X agent."}) is None


def test_exact_and_near_dedupe(tmp_path, home):
    base = "Bank the 1 off the right long rail straight across into the left side pocket with a center hit and medium speed"
    rows = [_qa("q1", base), _qa("q1", base + "  "), _qa("q1", base.replace("medium", "medium firm")), _qa("q2", "something else entirely different here ok")]
    res = build(_cfg(tmp_path, rows), dry_run=True)
    t = res.manifest["totals"]
    assert t["dropped_exact_dup"] == 1 and t["dropped_near_dup"] == 1 and t["kept"] == 2
    nd = NearDedupe(0.85)
    assert nd.add_if_new(base) and not nd.add_if_new(base + " .")
    assert exact_key("Hello, World") == exact_key("hello world")


def test_scrub_drops_secrets_and_redacts_pii(tmp_path, home):
    key = "sk-" + "A1b2C3d4" * 5
    rows = [_qa("leak", f"use {key} now"), _qa("pii", r"mail a@b.com, see C:\Users\alice\x and /home/bob/y, tsmit did it")]
    res = build(_cfg(tmp_path, rows, redact_usernames=["tsmit"]), dry_run=True)
    assert res.manifest["totals"]["dropped_secret"] == 1
    assert res.manifest["secret_kinds_dropped"] == {"openai_key": 1}
    text = json.dumps(res.train + res.eval)
    assert key not in text and "a@b.com" not in text and "alice" not in text and "bob" not in text and "tsmit" not in text
    assert find_secrets("task-orchestrator-default-run-abcdefghijklmnopqrstuvwxyz0123") == []
    assert redact(r"C:\Users\tsmit\x") == r"C:\Users\<USER>\x"


def test_length_filter(tmp_path, home):
    rows = [_qa("long", "word " * 3000), _qa("ok", "a fine answer")]
    res = build(_cfg(tmp_path, rows, max_tokens=1024), dry_run=True)
    assert res.manifest["totals"]["dropped_long"] == 1 and res.manifest["totals"]["kept"] == 1


def test_split_deterministic_and_stratified(tmp_path, home):
    rows = [_qa(f"question {i}", f"distinct answer number {i} " + "x" * (i % 7) + f" {i * 7919}") for i in range(50)]
    a = build(_cfg(tmp_path, rows), dry_run=True)
    b = build(_cfg(tmp_path, rows), dry_run=True)
    assert [r["id"] for r in a.eval] == [r["id"] for r in b.eval]
    assert a.manifest["sha256"] == b.manifest["sha256"]
    assert len(a.eval) == 5 and len(a.train) == 45
    c = build(_cfg(tmp_path, rows, seed=7), dry_run=True)
    assert [r["id"] for r in c.eval] != [r["id"] for r in a.eval]


def test_dry_run_writes_nothing(tmp_path, home):
    res = build(_cfg(tmp_path, [_qa("q", "answer here")]), dry_run=True)
    assert not (home / "datasets").exists()
    assert res.manifest["dry_run"] is True


def test_real_run_writes_only_inside_home(tmp_path, home):
    res = build(_cfg(tmp_path, [_qa("q", "answer here"), _qa("q2", "another answer")]), today="2026-10-10")
    out = home / "datasets" / "t-2026-10-10"
    assert res.out_dir == out
    assert sorted(p.name for p in out.iterdir()) == ["eval.jsonl", "manifest.json", "train.jsonl"]
    files = {p for p in tmp_path.rglob("*") if p.is_file()}
    assert all(str(p).startswith(str(home)) or p.name == "src.jsonl" for p in files)
    m = json.loads((out / "manifest.json").read_text())
    assert m["sources"]["s"]["kept"] == 2 and m["licenses"] == {"own": 2}


def test_name_cannot_escape_home(tmp_path, home):
    with pytest.raises(ValueError):
        build(_cfg(tmp_path, [_qa("q", "a b")], name="../../escape"), dry_run=True)


def test_vendor_chat_excluded_by_default(tmp_path, home):
    src = _write(tmp_path / "chat.jsonl", [_qa("q", "vendor answer")])
    cfg = {"name": "t", "min_tokens": 1, "sources": [{"name": "ide", "type": "ide_chat", "paths": [str(src)]}]}
    assert build(cfg, dry_run=True).manifest["totals"]["kept"] == 0
    assert build({**cfg, "allow_vendor_chat": True}, dry_run=True).manifest["totals"]["kept"] == 1


def test_grounded_doc_and_shot_pairs():
    md = "---\nname: Tester\ndescription: Tests contracts.\n---\n# T\n## Core Rules\n- Always run the full test suite before any deploy step happens.\n"
    pairs = list(agent_md_pairs(md, "tester"))
    assert pairs[0][1]["content"] == "Tests contracts."
    assert "Always run the full test suite" in pairs[1][1]["content"]
    shot = {"name": "Cross-Side Bank", "setup": ["1-ball: on the foot string.", "Route: CB → 1-ball → right long rail → left side pocket."],
            "objectBall": "1-ball", "pocket": "Left side pocket", "successLooksLike": "The 1 drops."}
    out = list(shot_pairs(shot))
    assert "Route: CB → 1-ball → right long rail → left side pocket." in out[0][1]["content"]
    assert out[-1][1]["content"] == "The 1 drops."
