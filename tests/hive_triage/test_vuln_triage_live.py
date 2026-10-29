"""vuln_triage LIVE gate: golden cases on real `npm audit --json` output (npm 10.9.8, auditReportVersion 2)
+ HTTP integration via /v1/tools/execute.

fixtures/npm_audit/npm10_vulnerable.json: `npm audit --json` for a throwaway package.json pinning
minimist 1.2.0, lodash 4.17.15, next 13.5.0, axios 0.21.0 (lockfile-only, --ignore-scripts).
fixtures/npm_audit/npm10_clean.json: same command with minimist 1.2.8. Tokens below are obviously fake.
"""
import copy
import json
import socket
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from abilities import vuln_triage as V

FIX = Path(__file__).parent / "fixtures" / "npm_audit"
FAKE = "FAKE-test-token-not-a-secret-0000"


def load(name):
    return json.loads((FIX / name).read_text(encoding="utf-8"))


def test_real_audit_golden():
    audit = load("npm10_vulnerable.json")
    assert audit["auditReportVersion"] == 2
    snap = copy.deepcopy(audit)
    out = V.run(context={"audit": audit})
    assert audit == snap and out["ok"] and out["read_only"] is True
    assert out["summary"] == {"packages": 6, "override": 3, "major_bump": 3, "no_fix": 0, "owner_flagged": 3}
    assert out["suggested_overrides"] == {"axios": ">=0.21.4", "lodash": ">=4.18.1", "minimist": ">=1.2.8"}
    by = {p["package"]: p for p in out["packages"]}
    assert [p["package"] for p in out["packages"]][:2] == ["minimist", "next"]  # critical first, then by name
    assert by["minimist"]["severity"] == "critical" and by["minimist"]["action"] == "override"
    assert by["next"]["action"] == "major-bump" and by["next"]["owner_flag"] is True
    # transitive vulns fixed only by a next major are routed to next, not overridden
    for dep in ("postcss", "zod"):
        assert by[dep]["action"] == "major-bump" and "bump next" in by[dep]["suggestion"]
    assert all("lockfile" in p["suggestion"] or p["action"] == "no-fix" for p in out["packages"])
    assert sum(p["advisories"] for p in out["packages"]) >= len(out["packages"])


def test_real_clean_audit():
    out = V.run(context={"audit": load("npm10_clean.json")})
    assert out["ok"] and out["summary"]["packages"] == 0 and out["suggested_overrides"] == {}


def test_real_audit_as_json_string_and_wrapped():
    raw = (FIX / "npm10_vulnerable.json").read_text(encoding="utf-8")
    assert V.run(input=raw)["summary"]["packages"] == 6
    assert V.run(context={"audit": {"audit": json.loads(raw)}})["summary"]["packages"] == 6


def test_real_audit_no_network(monkeypatch):
    def boom(*a, **k):
        raise AssertionError("network used")
    monkeypatch.setattr(socket, "create_connection", boom)
    assert V.run(context={"audit": load("npm10_vulnerable.json")})["ok"]


def test_status_live():
    assert V.ABILITY["status"] == "LIVE"
    from realai.ability_catalog import RUNDOWN_ABILITIES
    assert [e["status"] for e in RUNDOWN_ABILITIES if e["id"] == "vuln_triage"] == ["LIVE"]


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


@pytest.mark.parametrize("name", ["vuln_triage", "ability.vuln_triage"])
def test_http_tools_execute(server, monkeypatch, name):
    for k in ("REALAI_TOOLS_AUTH", "REALAI_ENV", "REALAI_TOOLS_ALLOW"):
        monkeypatch.delenv(k, raising=False)
    code, body = post(server, {"name": name, "arguments": {"audit": load("npm10_vulnerable.json")}})
    assert code == 200, body
    assert _result(body)["summary"]["packages"] == 6, body


def test_http_with_tool_auth_on(server, monkeypatch):
    from realai.orchestration import tool_auth

    monkeypatch.setattr(tool_auth, "_limiter", None)
    monkeypatch.delenv("REALAI_TOOLS_ALLOW", raising=False)
    monkeypatch.setenv("REALAI_TOOLS_AUTH", "1")
    monkeypatch.setenv("REALAI_TOOLS_TOKEN", FAKE)
    args = {"name": "ability.vuln_triage", "arguments": {"audit": load("npm10_vulnerable.json")}}
    assert post(server, args)[0] == 401
    code, body = post(server, args, token=FAKE)
    assert code == 200 and _result(body)["summary"]["major_bump"] == 3, body