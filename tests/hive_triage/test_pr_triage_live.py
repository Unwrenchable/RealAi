"""pr_triage LIVE gate: golden cases on real `gh pr view --json` captures + HTTP integration via /v1/tools/execute.

Fixtures in fixtures/pr/ are real captures from this repo (gh pr view <n> --json number,state,isDraft,
mergeable,mergeStateStatus,reviewDecision,statusCheckRollup). Tokens below are obviously fake.
"""
import copy
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from abilities import pr_triage as P

FIX = Path(__file__).parent / "fixtures" / "pr"
FAKE = "FAKE-test-token-not-a-secret-0000"


def load(n):
    return json.loads((FIX / f"pr_{n}.json").read_text(encoding="utf-8-sig"))


def green_open():
    """PR #212's real all-green rollup, as it looked while open and clean."""
    p = load(212)
    p.update(state="OPEN", mergeable="MERGEABLE", mergeStateStatus="CLEAN")
    return p


GOLDEN = [
    ("real #210 checks in progress", lambda: load(210), "needs-owner"),
    ("real #211 merged", lambda: load(211), "needs-owner"),
    ("real #212 merged", lambda: load(212), "needs-owner"),
    ("real #204 closed", lambda: load(204), "needs-owner"),
    ("#212 rollup, open + clean", green_open, "mergeable"),
    ("#212 rollup, conflicting", lambda: dict(green_open(), mergeable="CONFLICTING", mergeStateStatus="DIRTY"), "needs-rebase"),
    ("#212 rollup, behind base", lambda: dict(green_open(), mergeStateStatus="BEHIND"), "needs-rebase"),
    ("#212 rollup, draft", lambda: dict(green_open(), isDraft=True), "needs-owner"),
    ("#212 rollup, changes requested", lambda: dict(green_open(), reviewDecision="CHANGES_REQUESTED"), "needs-owner"),
]


def _failing():
    p = green_open()
    for c in p["statusCheckRollup"]:
        if c.get("name") == "python-tests":
            c["conclusion"] = "FAILURE"
    return p


GOLDEN.append(("#212 rollup, python-tests failed", _failing, "failing-check"))


@pytest.mark.parametrize("label,make,expected", GOLDEN, ids=[g[0] for g in GOLDEN])
def test_golden(label, make, expected):
    pr = make()
    snap = copy.deepcopy(pr)
    out = P.run(context={"pr": pr})
    assert out["ok"] and out["read_only"] is True and out["reason"]
    assert out["verdict"] == expected, (label, out)
    assert pr == snap


def test_failing_reason_names_the_check():
    assert "python-tests" in P.run(context={"pr": _failing()})["reason"]


def test_status_live():
    assert P.ABILITY["status"] == "LIVE"
    from realai.ability_catalog import RUNDOWN_ABILITIES
    assert [e["status"] for e in RUNDOWN_ABILITIES if e["id"] == "pr_triage"] == ["LIVE"]


# ---------------------------------------------------------------- HTTP integration
@pytest.fixture(scope="module")
def server():
    from realai.orchestration import v3_orchestrator as O

    srv = ThreadingHTTPServer(("127.0.0.1", 0), O.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1]
    srv.shutdown()
    srv.server_close()


def post(port, body, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/tools/execute",
                                 data=json.dumps(body).encode(), method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8") or "{}")


def _result(body):
    return body.get("result", body)


@pytest.mark.parametrize("name", ["pr_triage", "ability.pr_triage"])
def test_http_tools_execute(server, monkeypatch, name):
    for k in ("REALAI_TOOLS_AUTH", "REALAI_ENV", "REALAI_TOOLS_ALLOW"):
        monkeypatch.delenv(k, raising=False)
    code, body = post(server, {"name": name, "arguments": {"pr": green_open()}})
    assert code == 200, body
    assert _result(body)["verdict"] == "mergeable", body


def test_http_with_tool_auth_on(server, monkeypatch):
    from realai.orchestration import tool_auth

    monkeypatch.setattr(tool_auth, "_limiter", None)
    monkeypatch.delenv("REALAI_TOOLS_ALLOW", raising=False)
    monkeypatch.setenv("REALAI_TOOLS_AUTH", "1")
    monkeypatch.setenv("REALAI_TOOLS_TOKEN", FAKE)
    args = {"name": "ability.pr_triage", "arguments": {"pr": _failing()}}
    assert post(server, args)[0] == 401
    code, body = post(server, args, token=FAKE)
    assert code == 200 and _result(body)["verdict"] == "failing-check", body
