"""scripts/hive_ingest.py tests: allowlist, rejects, dedupe, mapping, dry-run, prune. All data synthetic."""
import importlib.util
import json
import sys
import uuid
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("hive_ingest", ROOT / "scripts" / "hive_ingest.py")
H = importlib.util.module_from_spec(_spec)
sys.modules["hive_ingest"] = H
_spec.loader.exec_module(H)

ABILITY_SURFACE = ROOT / "training" / "data" / "ability_surface.jsonl"


def rec(bot="Chief", **over):
    r = {
        "schema_version": "hive.v1", "id": str(uuid.uuid4()), "ts": "2026-10-27T09:15:00-07:00",
        "bot": {"name": bot, "id": "bot-test"}, "product": "RealAI",
        "task": {"ask": "Check PR #7 and report", "category": "pr_triage"},
        "actions": [{"step": 1, "tool_kind": "gh", "summary": "read checks"}],
        "verification": {"command": "gh pr checks 7", "result": "pass", "evidence": "3/3 passed"},
        "outcome": "done", "blockers": [], "links": ["https://github.com/example/repo/pull/7"],
        "reviewer": "QA Lead", "approval": None,
        "redaction": {"scanned": True, "scanner_version": "hive-redact-1"},
    }
    r.update(over)
    return r


def write(inbox, day, bot_file, records):
    d = inbox / day
    d.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(x) if not isinstance(x, str) else x for x in records]
    (d / f"{bot_file}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(inbox, out, **kw):
    kw.setdefault("run_date", "2026-10-27")
    return H.ingest(inbox, out, **kw)


def test_keeps_valid_and_maps_exactly_to_ability_surface_shape(tmp_path):
    inbox, out = tmp_path / "inbox", tmp_path / "out"
    write(inbox, "2026-10-27", "chief", [rec()])
    res = run(inbox, out)
    assert res["stats"]["kept"] == 1 and res["stats"]["rejected"] == 0
    cand = out / "hive_candidates_2026-10-27.jsonl"
    row = json.loads(cand.read_text(encoding="utf-8").splitlines()[0])
    assert list(row.keys()) == ["messages"]
    assert [m["role"] for m in row["messages"]] == ["user", "assistant"]
    assert all(list(m.keys()) == ["role", "content"] for m in row["messages"])
    assert "gh pr checks 7" in row["messages"][1]["content"]
    man = json.loads((out / "hive_candidates_2026-10-27.manifest.jsonl").read_text().splitlines()[0])
    assert set(man) == {"id", "content_hash", "bot", "category", "source", "line"}


@pytest.mark.skipif(not ABILITY_SURFACE.exists(), reason="ability_surface.jsonl not present")
def test_row_shape_matches_real_ability_surface_rows(tmp_path):
    first = json.loads(ABILITY_SURFACE.read_text(encoding="utf-8").splitlines()[0])
    mine = H.to_ability_row(rec())
    assert list(mine.keys()) == list(first.keys())
    assert [list(m.keys()) for m in mine["messages"]] == [list(m.keys()) for m in first["messages"]]
    assert [m["role"] for m in mine["messages"]] == [m["role"] for m in first["messages"]]


def test_allowlist_defaults_and_override(tmp_path):
    inbox, out = tmp_path / "inbox", tmp_path / "out"
    write(inbox, "2026-10-27", "chief", [rec("Chief")])
    write(inbox, "2026-10-27", "qa-lead", [rec("QA Lead", task={"ask": "different ask", "category": "ci_fix"})])
    write(inbox, "2026-10-27", "release-devops", [rec("Release & DevOps", task={"ask": "third ask", "category": "deploy"})])
    write(inbox, "2026-10-27", "random-bot", [rec("Random Bot")])
    res = run(inbox, out, dry_run=True)
    assert res["stats"]["kept"] == 3 and res["stats"]["skipped_files"] == 1
    res2 = run(inbox, out, allowlist=["Random Bot"], dry_run=True)
    assert res2["stats"]["kept"] == 1


def test_bot_name_must_match_file(tmp_path):
    inbox, out = tmp_path / "inbox", tmp_path / "out"
    write(inbox, "2026-10-27", "chief", [rec("QA Lead")])
    res = run(inbox, out)
    assert res["stats"]["kept"] == 0 and "bot:file_mismatch" in res["rejects"][0]["reasons"]


def test_missing_verification_and_bad_json_rejected(tmp_path):
    inbox, out = tmp_path / "inbox", tmp_path / "out"
    bad = rec()
    del bad["verification"]
    write(inbox, "2026-10-27", "chief", [bad, "{not json"])
    res = run(inbox, out)
    assert res["stats"]["kept"] == 0 and res["stats"]["rejected"] == 2
    reasons = [r for x in res["rejects"] for r in x["reasons"]]
    assert "verification:missing" in reasons and "json:invalid" in reasons


# Synthetic planted secrets, assembled at runtime so no credential-looking literal is committed.
PLANTED = {
    "github_token": "ghp_" + "FAKE" * 6,
    "openai_style": "sk-" + "FAKE" * 6,
    "db_url": "postgres://fakeuser:fakepw@db.example.test:5432/fake",
    "env_line": "API_KEY=fake-fake-fake",
    "pem": "-----BEGIN " + "PRIVATE KEY-----",
    "seed": "abandon ability able about above absent absorb abstract absurd abuse access accident",
}


@pytest.mark.parametrize("name", sorted(PLANTED))
@pytest.mark.parametrize("where", ["ask", "summary", "evidence", "blocker", "command"])
def test_planted_secrets_are_rejected_everywhere(tmp_path, name, where):
    inbox, out = tmp_path / "inbox", tmp_path / "out"
    r = rec()
    s = PLANTED[name]
    if where == "ask":
        r["task"]["ask"] = "do this " + s
    elif where == "summary":
        r["actions"][0]["summary"] = s
    elif where == "evidence":
        r["verification"]["evidence"] = s
    elif where == "blocker":
        r["blockers"] = [s]
    else:
        r["verification"]["command"] = "run " + s
    write(inbox, "2026-10-27", "chief", [r])
    res = run(inbox, out)
    assert res["stats"]["kept"] == 0 and res["stats"]["rejected"] == 1
    assert any(x.startswith("secret:") for x in res["rejects"][0]["reasons"])
    # nothing from the secret may reach any output file
    for f in out.glob("*"):
        assert s not in f.read_text(encoding="utf-8")
    assert not (out / "hive_candidates_2026-10-27.jsonl").exists()


def test_rejects_report_has_reasons_only(tmp_path):
    inbox, out = tmp_path / "inbox", tmp_path / "out"
    r = rec()
    r["task"]["ask"] = "leak " + PLANTED["github_token"]
    write(inbox, "2026-10-27", "chief", [r])
    run(inbox, out)
    rep = json.loads((out / "hive_rejects_2026-10-27.json").read_text(encoding="utf-8"))
    entry = rep["rejects"][0]
    assert set(entry) == {"file", "line", "id", "reasons"}
    text = json.dumps(rep)
    assert "leak" not in text and PLANTED["github_token"] not in text and "Check PR" not in text


def test_non_uuid_id_not_echoed_in_report(tmp_path):
    inbox, out = tmp_path / "inbox", tmp_path / "out"
    r = rec(id="id-" + PLANTED["github_token"])
    write(inbox, "2026-10-27", "chief", [r])
    res = run(inbox, out)
    assert res["rejects"][0]["id"] is None
    assert PLANTED["github_token"] not in (out / "hive_rejects_2026-10-27.json").read_text(encoding="utf-8")


def test_dedupe_by_id_and_content_hash_and_across_runs(tmp_path):
    inbox, out = tmp_path / "inbox", tmp_path / "out"
    a = rec()
    same_id = rec(id=a["id"], task={"ask": "different", "category": "other"})
    same_content = rec()  # new id/ts, identical content
    same_content["ts"] = "2026-10-27T10:00:00-07:00"
    write(inbox, "2026-10-27", "chief", [a, same_id, same_content])
    res = run(inbox, out)
    assert res["stats"]["kept"] == 1 and res["stats"]["duplicates"] == 2
    res2 = run(inbox, out)  # idempotent re-run
    assert res2["stats"]["kept"] == 0 and res2["stats"]["duplicates"] >= 1
    lines = (out / "hive_candidates_2026-10-27.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1


def test_dry_run_writes_nothing(tmp_path, capsys):
    inbox, out = tmp_path / "inbox", tmp_path / "out"
    write(inbox, "2026-10-27", "chief", [rec()])
    rc = H.main([str(inbox), "--out-dir", str(out), "--dry-run"])
    assert rc == 0 and not out.exists()
    assert "dry-run" in capsys.readouterr().out


def test_date_filter(tmp_path):
    inbox, out = tmp_path / "inbox", tmp_path / "out"
    write(inbox, "2026-10-26", "chief", [rec()])
    write(inbox, "2026-10-27", "chief", [rec(task={"ask": "other", "category": "data"})])
    res = run(inbox, out, only_date="2026-10-27", dry_run=True)
    assert res["stats"]["kept"] == 1


def test_never_writes_ability_surface_or_hive_ops(tmp_path):
    inbox, out = tmp_path / "inbox", tmp_path / "out"
    write(inbox, "2026-10-27", "chief", [rec()])
    run(inbox, out)
    assert sorted(p.name for p in out.iterdir() if p.is_file()) == [
        "hive_candidates_2026-10-27.jsonl", "hive_candidates_2026-10-27.manifest.jsonl",
        "hive_rejects_2026-10-27.json"]


def test_prune_lists_only_unless_apply(tmp_path, capsys):
    inbox = tmp_path / "inbox"
    write(inbox, "2026-01-01", "chief", [rec()])
    write(inbox, date.today().isoformat(), "chief", [rec()])
    old = inbox / "2026-01-01" / "chief.jsonl"
    # list only: nothing deleted
    assert H.prune(inbox, 90) == [old]
    assert old.exists()
    assert H.main([str(inbox), "--prune-older-than-days", "90"]) == 0
    assert old.exists() and "would delete" in capsys.readouterr().out
    # apply: deletes only the old raw file
    assert H.main([str(inbox), "--prune-older-than-days", "90", "--apply"]) == 0
    assert not old.exists() and not (inbox / "2026-01-01").exists()
    assert (inbox / date.today().isoformat() / "chief.jsonl").exists()


def test_apply_without_prune_is_an_error(tmp_path):
    with pytest.raises(SystemExit):
        H.main([str(tmp_path), "--apply"])


def test_missing_inbox_is_empty_not_crash(tmp_path):
    res = run(tmp_path / "nope", tmp_path / "out", dry_run=True)
    assert res["stats"]["records"] == 0
