"""pr_triage, vuln_triage, ci_failure_classify: fixtures, purity (no writes/network), catalog and routing."""
import copy
import json
import os
import socket

import pytest

from abilities import ci_failure_classify as C
from abilities import pr_triage as P
from abilities import vuln_triage as V


# ---------------------------------------------------------------- pr_triage
def pr(**over):
    base = {"state": "OPEN", "isDraft": False, "mergeable": "MERGEABLE", "mergeStateStatus": "CLEAN",
            "reviewDecision": None,
            "checks": [{"name": "python-tests", "state": "SUCCESS"}, {"name": "node-workspace", "state": "SUCCESS"}]}
    base.update(over)
    return base


def verdict(**over):
    out = P.run(context={"pr": pr(**over)})
    assert out["ok"] and out["read_only"] is True and out["reason"]
    return out["verdict"]


def test_pr_mergeable():
    assert verdict() == "mergeable"


def test_pr_needs_rebase_variants():
    assert verdict(mergeable="CONFLICTING", mergeStateStatus="DIRTY") == "needs-rebase"
    assert verdict(mergeStateStatus="BEHIND") == "needs-rebase"


def test_pr_failing_check_beats_pending_and_names_it():
    out = P.run(context={"pr": pr(checks=[{"name": "python-tests", "state": "FAILURE"},
                                          {"name": "node", "state": "PENDING"}])})
    assert out["verdict"] == "failing-check" and "python-tests" in out["reason"]
    for bucket in ("fail", "cancel"):
        assert verdict(checks=[{"name": "x", "bucket": bucket}]) == "failing-check"


def test_pr_rollup_shape():
    ok = [{"name": "a", "status": "COMPLETED", "conclusion": "SUCCESS"}]
    bad = [{"name": "a", "status": "COMPLETED", "conclusion": "FAILURE"}]
    run_ = [{"name": "a", "status": "IN_PROGRESS", "conclusion": ""}]
    assert P.run(context={"pr": {"statusCheckRollup": ok}})["verdict"] == "mergeable"
    assert P.run(context={"pr": {"statusCheckRollup": bad}})["verdict"] == "failing-check"
    assert P.run(context={"pr": {"statusCheckRollup": run_}})["verdict"] == "needs-owner"


def test_pr_needs_owner_cases():
    assert verdict(state="MERGED") == "needs-owner"
    assert verdict(state="CLOSED") == "needs-owner"
    assert verdict(isDraft=True) == "needs-owner"
    assert verdict(reviewDecision="CHANGES_REQUESTED") == "needs-owner"
    assert verdict(checks=[]) == "needs-owner"
    assert verdict(checks=[{"name": "a", "state": "PENDING"}]) == "needs-owner"
    assert verdict(mergeStateStatus="BLOCKED") == "needs-owner"
    assert verdict(mergeable="UNKNOWN") == "needs-owner"


def test_pr_accepts_json_string_and_bad_input():
    out = P.run(input=json.dumps({"pr": pr()}))
    assert out["verdict"] == "mergeable"
    assert P.run()["ok"] is False
    assert P.run(context={"pr": "nope"})["ok"] is False
    assert P.run(input="{not json")["ok"] is False


def test_pr_does_not_mutate_input():
    p = pr()
    snap = copy.deepcopy(p)
    P.run(context={"pr": p})
    assert p == snap


# ---------------------------------------------------------------- vuln_triage
AUDIT = {"vulnerabilities": {
    "minimist": {"name": "minimist", "severity": "critical", "isDirect": False,
                 "via": [{"source": 1, "name": "minimist", "title": "pp", "severity": "critical"}],
                 "fixAvailable": {"name": "minimist", "version": "1.2.8", "isSemVerMajor": False}},
    "zod": {"name": "zod", "severity": "moderate", "isDirect": True,
            "via": [{"source": 2, "name": "zod", "severity": "moderate"}, {"source": 3, "name": "zod", "severity": "low"}],
            "fixAvailable": {"name": "zod", "version": "4.0.0", "isSemVerMajor": True}},
    "old-lib": {"name": "old-lib", "severity": "high", "isDirect": False, "via": ["dep"], "fixAvailable": False},
    "tar": {"name": "tar", "severity": "high", "isDirect": False, "via": [{"source": 4}], "fixAvailable": True},
}}


def test_vuln_groups_and_suggests():
    out = V.run(context={"audit": AUDIT})
    assert out["ok"] and out["read_only"] is True
    by = {p["package"]: p for p in out["packages"]}
    assert by["minimist"]["action"] == "override" and not by["minimist"]["owner_flag"]
    assert by["zod"]["action"] == "major-bump" and by["zod"]["owner_flag"] is True
    assert by["zod"]["advisories"] == 2
    assert by["old-lib"]["action"] == "no-fix" and by["old-lib"]["owner_flag"]
    assert by["tar"]["action"] == "override"
    assert out["suggested_overrides"] == {"minimist": ">=1.2.8"}
    assert out["summary"] == {"packages": 4, "override": 2, "major_bump": 1, "no_fix": 1, "owner_flagged": 2}
    assert [p["package"] for p in out["packages"]][0] == "minimist"  # critical first
    assert "PR" in by["minimist"]["suggestion"] and "lockfile" in by["minimist"]["suggestion"]


def test_vuln_flat_rows_group_by_package():
    rows = [{"package": "lodash", "severity": "high", "current": "4.17.15", "fixed_in": "4.17.21"},
            {"package": "lodash", "severity": "critical", "current": "4.17.15", "fixed_in": "4.17.21"},
            {"package": "next", "severity": "moderate", "current": "13.5.0", "fixed_in": "15.0.1"}]
    out = V.run(context={"audit": rows})
    by = {p["package"]: p for p in out["packages"]}
    assert len(out["packages"]) == 2
    assert by["lodash"]["severity"] == "critical" and by["lodash"]["advisories"] == 2 and by["lodash"]["action"] == "override"
    assert by["next"]["action"] == "major-bump" and by["next"]["owner_flag"]


def test_vuln_errors_and_json_input():
    assert V.run()["ok"] is False
    assert V.run(context={"audit": "x"})["ok"] is False
    assert V.run(input=json.dumps(AUDIT))["ok"] is True
    assert V.run(context={"audit": {"vulnerabilities": {}}})["summary"]["packages"] == 0


def test_vuln_never_writes_files_or_uses_network(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def boom(*a, **k):
        raise AssertionError("network used")
    monkeypatch.setattr(socket, "socket", boom)
    monkeypatch.setattr(socket, "create_connection", boom)
    before = sorted(os.listdir(tmp_path))
    a = copy.deepcopy(AUDIT)
    out = V.run(context={"audit": a})
    assert out["ok"] and a == AUDIT
    assert sorted(os.listdir(tmp_path)) == before


# ---------------------------------------------------------------- ci_failure_classify
CASES = {
    "lockfile-conflict": [
        " ERR_PNPM_OUTDATED_LOCKFILE  Cannot install with \"frozen-lockfile\" because pnpm-lock.yaml is not up to date",
        "npm ERR! `npm ci` can only install packages when your package.json and package-lock.json are in sync",
        "CONFLICT (content): Merge conflict in pnpm-lock.yaml",
    ],
    "stale-branch": [
        "Automatic merge failed; fix conflicts and then commit the result.",
        "CONFLICT (content): Merge conflict in src/app.py",
        "This branch is out-of-date with the base branch",
    ],
    "env-missing": [
        "ModuleNotFoundError: No module named 'transformers'",
        "bash: pnpm: command not found",
        "Error: Missing required environment variable FAKE_SETTING",
        "KeyError: 'FAKE_SETTING'",
    ],
    "test-failure": [
        "FAILED tests/test_x.py::test_y - AssertionError: assert 1 == 2",
        "================ 2 failed, 40 passed in 3.2s ================",
        "Tests:       1 failed, 9 passed, 10 total",
    ],
}


@pytest.mark.parametrize("expected", sorted(CASES))
def test_classify_fixtures(expected):
    for log in CASES[expected]:
        out = C.run(context={"log": "step 1 ok\n" + log + "\nstep 2"})
        assert out["ok"] and out["classification"] == expected, (expected, log, out)
        assert out["next_step"] and out["read_only"] is True
        assert log not in json.dumps(out)  # result never echoes log text


def test_classify_unknown_and_flags():
    out = C.run(context={"log": "Run actions/checkout@v4\nDone."})
    assert out["classification"] == "unknown" and out["next_step"]
    out = C.run(context={"log": "Run actions/checkout@v4\nDone.", "branch_behind": True})
    assert out["classification"] == "stale-branch"
    assert C.run()["ok"] is False and C.run(context={"log": "   "})["ok"] is False


def test_classify_priority_lockfile_over_test_failure():
    log = "FAILED tests/test_x.py::test_y\n ERR_PNPM_OUTDATED_LOCKFILE  frozen-lockfile not up to date"
    assert C.run(context={"log": log})["classification"] == "lockfile-conflict"


def test_classify_input_string_and_huge_log():
    assert C.run(input="Automatic merge failed")["classification"] == "stale-branch"
    big = "x" * 1_000_000 + "\nAssertionError"
    assert C.run(context={"log": big})["classification"] == "test-failure"


# ---------------------------------------------------------------- registration
@pytest.mark.parametrize("mod", [P, V, C])
def test_ability_metadata_partial_and_secretless(mod):
    assert mod.ABILITY["status"] in ("PARTIAL", "LIVE") and mod.ABILITY["secrets_policy"] == "none"
    assert mod.ABILITY["dest"] == f"abilities/{mod.ABILITY['id']}.py"


@pytest.mark.parametrize("aid", ["pr_triage", "vuln_triage", "ci_failure_classify"])
def test_catalog_entry_partial_no_powers(aid):
    cat = pytest.importorskip("realai.ability_catalog")
    entries = [e for e in cat.RUNDOWN_ABILITIES if e["id"] == aid]
    assert len(entries) == 1, "catalog entry missing or catalog container renamed"
    e = entries[0]
    assert e["status"] in ("PARTIAL", "LIVE")  # LIVE gate: tests/hive_triage/test_<id>_live.py
    assert e["modules"] == [f"abilities/{aid}.py"]
    note = e["status_note"].lower()
    assert "read-only" in note and "no network" in note


def test_tools_execute_routing():
    bridge = pytest.importorskip("realai.orchestration.v3_runtime_bridge")
    out = bridge.execute_registry_tool("pr_triage", {"pr": pr()})
    assert out.get("ok") is True and out["verdict"] == "mergeable", out
    out = bridge.execute_registry_tool("vuln_triage", {"audit": AUDIT})
    assert out.get("ok") is True and out["summary"]["packages"] == 4, out
    out = bridge.execute_registry_tool("ci_failure_classify", {"log": CASES["env-missing"][0]})
    assert out.get("ok") is True and out["classification"] == "env-missing", out
