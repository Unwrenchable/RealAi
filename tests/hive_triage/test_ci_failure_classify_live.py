"""ci_failure_classify LIVE gate: golden cases on saved real CI logs + HTTP integration via /v1/tools/execute.

fixtures/ci_logs/*.log are the last 300 lines of `gh run view <id> --log-failed` for real failed runs of this repo
(40872653215, 40863858813, 40865311223, 40865135818, 40867823880). GitHub masks secrets in these logs;
the capture script also refused any token-shaped string. Tokens below are obviously fake.
"""
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

from abilities import ci_failure_classify as C

FIX = Path(__file__).parent / "fixtures" / "ci_logs"
FAKE = "FAKE-test-token-not-a-secret-0000"

GOLDEN = {
    "gha_pytest_failed": ("test-failure", "pytest_failed"),            # FAILED lines behind job/step/timestamp prefixes
    "gha_runner_failed_and_lint": ("test-failure", "repo_runner_failed"),
    "gha_runner_failed_py311_312": ("test-failure", "repo_runner_failed"),
    "gha_runner_failed_lint": ("test-failure", "repo_runner_failed"),
    "gha_dependabot_updater_error": ("unknown", "no_match"),           # updater crash: none of the classes, escalate
}


def log(name):
    return (FIX / f"{name}.log").read_text(encoding="utf-8")


@pytest.mark.parametrize("name", sorted(GOLDEN))
def test_real_ci_logs(name):
    text = log(name)
    out = C.run(context={"log": text})
    assert out["ok"] and out["read_only"] is True and out["next_step"]
    assert (out["classification"], out["rule"]) == GOLDEN[name], out
    blob = json.dumps(out)
    assert all(line not in blob for line in text.splitlines() if len(line) > 40)  # never echoes log text


def test_keyerror_on_a_dict_key_is_not_env_missing():
    # real log 40872653215 has `KeyError: 'RealAi'` from a test; only ALL_CAPS keys look like env vars
    assert C.run(context={"log": "E       KeyError: 'RealAi'"})["classification"] == "unknown"
    assert C.run(context={"log": "KeyError: 'FAKE_SETTING'"})["classification"] == "env-missing"


def test_prefix_strip_keeps_raw_logs_working():
    raw = "2026-10-29T12:23:47.6418363Z FAILED tests/test_x.py::test_y - boom"
    assert C.run(context={"log": raw})["rule"] == "pytest_failed"
    gha = "python-tests\tRun pytest\t" + raw
    assert C.run(context={"log": gha})["rule"] == "pytest_failed"


def test_status_live():
    assert C.ABILITY["status"] == "LIVE"
    from realai.ability_catalog import RUNDOWN_ABILITIES
    assert [e["status"] for e in RUNDOWN_ABILITIES if e["id"] == "ci_failure_classify"] == ["LIVE"]


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


@pytest.mark.parametrize("name", ["ci_failure_classify", "ability.ci_failure_classify"])
def test_http_tools_execute(server, monkeypatch, name):
    for k in ("REALAI_TOOLS_AUTH", "REALAI_ENV", "REALAI_TOOLS_ALLOW"):
        monkeypatch.delenv(k, raising=False)
    code, body = post(server, {"name": name, "arguments": {"log": log("gha_pytest_failed")}})
    assert code == 200, body
    assert _result(body)["classification"] == "test-failure", body


def test_http_with_tool_auth_on(server, monkeypatch):
    from realai.orchestration import tool_auth

    monkeypatch.setattr(tool_auth, "_limiter", None)
    monkeypatch.delenv("REALAI_TOOLS_ALLOW", raising=False)
    monkeypatch.setenv("REALAI_TOOLS_AUTH", "1")
    monkeypatch.setenv("REALAI_TOOLS_TOKEN", FAKE)
    args = {"name": "ability.ci_failure_classify", "arguments": {"log": log("gha_runner_failed_lint")}}
    assert post(server, args)[0] == 401
    code, body = post(server, args, token=FAKE)
    assert code == 200 and _result(body)["rule"] == "repo_runner_failed", body