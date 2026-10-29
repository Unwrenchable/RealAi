"""hive.v1 schema validator tests (all data is synthetic)."""
import copy
import uuid

from realai.hive_records.schema import validate_record


def good():
    return {
        "schema_version": "hive.v1",
        "id": str(uuid.uuid4()),
        "ts": "2026-10-27T09:15:00-07:00",
        "bot": {"name": "QA Lead", "id": "bot-test-001"},
        "product": "RealAI",
        "task": {"ask": "Triage open PR #1", "category": "pr_triage"},
        "actions": [{"step": 1, "tool_kind": "gh", "summary": "listed checks"}],
        "verification": {"command": "gh pr checks 1", "result": "pass", "evidence": "all checks passed"},
        "outcome": "done",
        "blockers": [],
        "links": ["https://github.com/example/repo/pull/1"],
        "reviewer": "Chief",
        "approval": "owner OK (synthetic)",
        "redaction": {"scanned": True, "scanner_version": "hive-redact-1"},
    }


def test_valid_record_passes():
    assert validate_record(good()) == []


def test_reviewer_and_approval_optional_and_nullable():
    r = good()
    del r["reviewer"]
    r["approval"] = None
    assert validate_record(r) == []


def test_missing_verification_rejected():
    r = good()
    del r["verification"]
    assert "verification:missing" in validate_record(r)
    r2 = good()
    r2["verification"] = {}
    assert "verification:missing" in validate_record(r2)
    r3 = good()
    r3["verification"] = None
    assert "verification:missing" in validate_record(r3)


def test_verification_fields_enforced():
    r = good()
    r["verification"]["result"] = "maybe"
    assert "verification.result:invalid" in validate_record(r)
    r = good()
    r["verification"]["evidence"] = "x" * 501
    assert "verification.evidence:invalid" in validate_record(r)
    r = good()
    r["verification"]["evidence"] = "x" * 500
    assert validate_record(r) == []
    r = good()
    del r["verification"]["command"]
    assert "verification.command:missing" in validate_record(r)


def test_bad_enums_rejected():
    for path, val, code in [
        (("task", "category"), "nope", "task.category:invalid"),
        (("outcome",), "great", "outcome:invalid"),
    ]:
        r = good()
        tgt = r
        for k in path[:-1]:
            tgt = tgt[k]
        tgt[path[-1]] = val
        assert code in validate_record(r)
    r = good()
    r["actions"][0]["tool_kind"] = "bash"
    assert "actions[0].tool_kind:invalid" in validate_record(r)


def test_all_categories_and_tool_kinds_accepted():
    for c in ("pr_triage", "vuln_triage", "ci_fix", "dep_update", "deploy", "data", "other"):
        r = good()
        r["task"]["category"] = c
        assert validate_record(r) == []
    for t in ("git", "gh", "npm", "pnpm", "pytest", "http", "other"):
        r = good()
        r["actions"][0]["tool_kind"] = t
        assert validate_record(r) == []


def test_id_must_be_uuid():
    r = good()
    r["id"] = "not-a-uuid"
    assert "id:invalid_uuid" in validate_record(r)


def test_ts_requires_offset():
    r = good()
    r["ts"] = "2026-10-27T09:15:00"
    assert "ts:invalid_iso8601_offset" in validate_record(r)
    r["ts"] = "yesterday"
    assert "ts:invalid_iso8601_offset" in validate_record(r)
    r["ts"] = "2026-10-27T16:15:00Z"
    assert validate_record(r) == []


def test_links_http_only():
    for bad in ["ftp://example.com/x", "javascript:alert(1)", "file:///etc/passwd", "example.com", "http://"]:
        r = good()
        r["links"] = [bad]
        assert "links[0]:not_http_url" in validate_record(r), bad
    r = good()
    r["links"] = ["http://example.com/a", "https://example.com/b"]
    assert validate_record(r) == []


def test_schema_version_and_unknown_fields():
    r = good()
    r["schema_version"] = "hive.v2"
    assert "schema_version:invalid" in validate_record(r)
    r = good()
    r["extra"] = "x"
    assert "record:unknown_field" in validate_record(r)
    r = good()
    r["task"]["extra"] = "x"
    assert "task:unknown_field" in validate_record(r)


def test_redaction_attestation_required_true():
    r = good()
    r["redaction"]["scanned"] = False
    assert "redaction.scanned:not_true" in validate_record(r)
    r = good()
    del r["redaction"]
    assert "redaction:missing" in validate_record(r)


def test_actions_shape():
    r = good()
    r["actions"] = []
    assert "actions:invalid" in validate_record(r)
    r = good()
    r["actions"][0]["step"] = 0
    assert "actions[0].step:invalid" in validate_record(r)
    r = good()
    r["actions"][0]["summary"] = "s" * 501
    assert "actions[0].summary:invalid" in validate_record(r)


def test_non_object_and_error_codes_do_not_echo_values():
    assert validate_record([1, 2]) == ["record:not_object"]
    r = good()
    r["task"]["category"] = "SENTINEL_VALUE_XYZ"
    assert all("SENTINEL_VALUE_XYZ" not in e for e in validate_record(r))
    snapshot = copy.deepcopy(r)
    validate_record(r)
    assert r == snapshot  # validator never mutates
