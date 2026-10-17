"""Approval gate (Travis decision 5) + canonical self-heal (decision 3)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest


@pytest.fixture()
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("REALAI_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("REALAI_APPROVALS_STORE", str(tmp_path / ".approvals.json"))
    monkeypatch.setenv("APPROVALS_STORE", str(tmp_path / ".approvals.json"))
    monkeypatch.delenv("REALAI_APPROVALS_AUDIT", raising=False)
    (tmp_path / "README.md").write_text("# Title\nhello world\n", encoding="utf-8")
    return tmp_path


def _gate():
    from realai.core import approval_gate

    return approval_gate


def test_edit_request_is_pending_and_previews_diff(ws):
    g = _gate()
    r = g.request("search_replace", {"file_path": "README.md", "old_string": "hello", "new_string": "bye"})
    assert r["status"] == "pending" and r["executed"] is False
    assert "-hello world" in r["preview"]["diff"] and "+bye world" in r["preview"]["diff"]
    assert (ws / "README.md").read_text() == "# Title\nhello world\n"
    again = g.request("search_replace", {"file_path": "README.md", "old_string": "hello", "new_string": "bye"})
    assert again["approval_id"] == r["approval_id"] and len(json.loads((ws / ".approvals.json").read_text())["items"]) == 1


def test_execute_only_after_human_approval_and_once(ws):
    g = _gate()
    rid = g.request("search_replace", {"file_path": "README.md", "old_string": "hello", "new_string": "bye"})["approval_id"]
    assert g.execute(rid)["ok"] is False  # pending -> denied
    assert (ws / "README.md").read_text().endswith("hello world\n")
    assert g.set_status(rid, "approved", by="travis")
    out = g.execute(rid)
    assert out["ok"] is True and (ws / "README.md").read_text() == "# Title\nbye world\n"
    assert g.execute(rid)["ok"] is False  # single use
    events = [json.loads(line)["event"] for line in (ws / ".approvals.json.audit.jsonl").read_text().splitlines()]
    assert events[:3] == ["requested", "refused_execute", "approved"] and "executed" in events


def test_stale_and_rejected(ws):
    g = _gate()
    rid = g.request("search_replace", {"file_path": "README.md", "old_string": "hello", "new_string": "bye"})["approval_id"]
    g.set_status(rid, "approved", by="travis")
    (ws / "README.md").write_text("# Title\nhello world!\n", encoding="utf-8")
    assert "stale" in g.execute(rid)["error"]
    rid2 = g.request("write_file", {"file_path": "new.txt", "content": "x"})["approval_id"]
    g.set_status(rid2, "rejected", by="travis")
    assert g.execute(rid2)["ok"] is False and not (ws / "new.txt").exists()


@pytest.mark.parametrize("args", [
    {"file_path": "../outside.txt", "content": "x"},
    {"file_path": ".env", "content": "X=1"},
    {"file_path": ".approvals.json", "content": "{}"},
    {"file_path": ".git/config", "content": "x"},
    {"file_path": "keys/id.pem", "content": "x"},
])
def test_workspace_scope_and_protected_paths(ws, args):
    r = _gate().request("write_file", args)
    assert r["status"] == "refused" and r["executed"] is False


@pytest.mark.parametrize("cmd", ["solana transfer ABC 2", "spl-token transfer x 1 y", "python send_sol.py",
                                 "python -c 'import json' && cat .approvals.json"])
def test_money_and_store_tampering_refused(ws, cmd):
    r = _gate().request("run_terminal_command", {"command": cmd})
    assert r["status"] == "refused"


def test_command_runs_in_workspace_after_approval(ws):
    g = _gate()
    r = g.request("run_terminal_command", {"command": "echo hi > marker.txt"})
    assert r["status"] == "pending" and not (ws / "marker.txt").exists()
    assert r["preview"]["cwd"] == "."
    g.set_status(r["approval_id"], "approved", by="travis")
    assert g.execute(r["approval_id"])["ok"] and (ws / "marker.txt").exists()


def test_orchestrator_exec_tools_are_gated(ws):
    from realai.orchestration import v3_orchestrator as orch

    r = orch._run_tool("run_command", {"command": "echo hi > orch_marker.txt"})
    assert r["status"] == "pending" and r["executed"] is False and not (ws / "orch_marker.txt").exists()
    r2 = orch._run_tool("search_replace", {"target_file": "README.md", "old_string": "hello", "new_string": "x"})
    assert r2["status"] == "pending" and "hello" in (ws / "README.md").read_text()
    bogus = orch._run_tool("run_command", {"command": "echo hi", "approval_id": r2["approval_id"]})
    assert bogus["executed"] is False  # an approval for another action never unlocks this one
    for name in ("self_repair", "self_extend", "auto_wire", "run_script"):
        assert orch._run_tool(name, {"code": "print(1)", "reason": "t"})["status"] in ("pending", "refused")


def test_hive_executor_ignores_model_supplied_approved_flag(ws, monkeypatch):
    monkeypatch.chdir(ws)
    monkeypatch.delenv("REALAI_APPROVAL_TRUST_FLAG", raising=False)
    from realai.core.tools import hive_executor as hx

    assert hx._approval_confirm("dangerous_tool_x", {"approved": True}) is False
    info = hx._APPROVAL_STATE.info
    assert info["approval_status"] == "pending" and info["approval_id"]
    store = hx._load_approval_store()
    items = [i for i in store.list_requests() if (i.get("payload") or {}).get("tool") == "dangerous_tool_x"]
    assert items and items[-1]["status"] == "pending" and "approved" not in items[-1]["payload"]["arguments"]
    assert (ws / ".approvals.json").exists()  # the one shared store (env-pinned to the test workspace)


def test_hive_executor_files_request_even_when_plugins_tools_package_fails(ws, monkeypatch):
    import builtins

    from realai.core.tools import hive_executor as hx

    real_import = builtins.__import__

    def broken(name, *a, **k):
        if name.startswith("realai.plugins.tools"):
            raise ImportError("simulated: core.security missing")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", broken)
    assert hx._approval_confirm("dangerous_tool_y", {}) is False
    monkeypatch.setattr(builtins, "__import__", real_import)
    assert hx._APPROVAL_STATE.info["approval_status"] == "pending"
    data = json.loads((ws / ".approvals.json").read_text(encoding="utf-8"))
    assert any((i.get("payload") or {}).get("tool") == "dangerous_tool_y" for i in data["items"])


def test_hive_executor_reports_clear_error_when_store_unreachable(ws, monkeypatch):
    from realai.core.tools import hive_executor as hx

    def boom():
        raise RuntimeError("approvals store unavailable (simulated)")

    monkeypatch.setattr(hx, "_load_approval_store", boom)
    assert hx._approval_confirm("dangerous_tool_z", {}) is False
    info = hx._APPROVAL_STATE.info
    assert info["approval_status"] == "error" and "simulated" in info["approval_error"]


def test_exec_ungated_escape_hatch_is_gone(monkeypatch):
    monkeypatch.setenv("REALAI_EXEC_UNGATED", "1")
    assert _gate().gated_action("run_command") == "run_terminal_command"
    import inspect

    assert "REALAI_EXEC_UNGATED" not in inspect.getsource(_gate())


def test_single_store_resolution(monkeypatch, tmp_path):
    from realai.core import approvals_config as ac

    monkeypatch.delenv("REALAI_APPROVALS_STORE", raising=False)
    monkeypatch.delenv("APPROVALS_STORE", raising=False)
    cfg = tmp_path / "c.json"
    cfg.write_text(json.dumps({"store": str(tmp_path / "w.json"), "store_posix": str(tmp_path / "p.json")}), encoding="utf-8")
    monkeypatch.setenv("REALAI_APPROVALS_CONFIG", str(cfg))
    assert ac.store_path().name == ("w.json" if os.name == "nt" else "p.json")
    monkeypatch.setenv("REALAI_APPROVALS_CONFIG", str(tmp_path / "missing.json"))
    if os.name == "nt":
        assert str(ac.store_path()) == r"C:\RealAI-clean\.approvals.json"
    else:
        assert "realai-approvals" in str(ac.store_path())
    monkeypatch.setenv("APPROVALS_STORE", str(tmp_path / "e.json"))
    assert ac.store_path() == tmp_path / "e.json" == _gate().store_path()
    repo_cfg = json.loads((Path(ac.__file__).resolve().parents[2] / "config" / "approvals.json").read_text(encoding="utf-8"))
    assert repo_cfg["store"] == r"C:\RealAI-clean\.approvals.json"


def test_hive_request_approval_tool_is_request_only_and_sandboxed(ws):
    from realai import hive_tools
    from realai.hive_tools.approvals import contract_violation

    assert "request_approval" in hive_tools.NEW_TOOLS
    a = {"action": "run_terminal_command", "command": "git status", "reason": "user asked"}
    r1 = hive_tools.execute("request_approval", a, offline=True)
    r2 = hive_tools.execute("request_approval", a, offline=True)
    assert r1 == r2 and r1["status"] == "pending" and r1["executed"] is False and contract_violation(r1) == ""
    assert not (ws / ".approvals.json").exists()  # sandbox store, not the real queue
    money = hive_tools.execute("request_approval", {"action": "run_terminal_command", "command": "solana transfer X 2",
                                                    "reason": "pay"}, offline=True)
    assert money["status"] == "refused"
    assert contract_violation({"status": "approved", "executed": True})
    assert not any(n in hive_tools.EXECUTORS for n in ("approve", "execute_approval", "run_command", "search_replace"))
    live = hive_tools.execute("request_approval", a, offline=False)
    assert live["status"] == "pending" and (ws / ".approvals.json").exists()


def test_verify_flags_executed_approval():
    from realai.training.self_data.verify import recompute_check

    bad = [{"name": "request_approval", "arguments": {}, "result": {"status": "executed", "executed": True}}]
    assert "approval_executed_or_bypassed" in recompute_check(bad, "done")


def test_self_heal_canonical_in_core_with_shims(ws, monkeypatch):
    import realai.core.agents.self_heal as old_agent
    import realai.core.self_heal as core
    import realai.self_heal as old

    assert old is core and old_agent is core
    for fn in ("_probe_routes", "run_curated_promote", "run_deep_promote", "run_promote", "run_full_cycle",
               "run_discover", "run_assemble", "run_learn_keywords", "status", "abilities_manifest", "_run_py"):
        assert callable(getattr(old, fn))
    assert core._ROOT == Path(core.__file__).resolve().parents[2]
    monkeypatch.setenv("REALAI_SELF_IMPROVE", "1")
    called = []
    monkeypatch.setattr(core, "_run_py", lambda *a, **k: called.append(a) or {"ok": True})
    r = core.run_curated_promote(apply=True)
    assert r["status"] == "pending" and r["action"] == "self_heal_curated_promote" and not called
    assert core.run_promote(apply=True)["status"] == "pending" and not called
