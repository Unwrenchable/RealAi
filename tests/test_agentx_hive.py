"""agentx hive: loader/converters, routing, team graphs, approval + sandbox gate, playtest loop."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from realai.agentx.hive.converters import agent_md_to_manifest, hive_role_json_to_manifest, parse_front_matter
from realai.agentx.hive.registry import load_registry


@pytest.fixture(autouse=True)
def _no_live_hive(monkeypatch):
    """Keep these unit tests offline even when a real hive is up on :8001."""
    monkeypatch.setenv("REALAI_AGENTX_USE_HIVE", "0")


def test_front_matter_parser_handles_folded_and_lists(tmp_path):
    p = tmp_path / "x.agent.md"
    p.write_text("---\nname: WastlandQA\ndescription: >\n  Master QA tester\n  for the wasteland\n"
                 "tools: [read_file, run_in_terminal]\n---\n# body\n", encoding="utf-8")
    meta, body = parse_front_matter(p.read_text())
    assert meta["name"] == "WastlandQA" and "Master QA tester for the wasteland" == meta["description"]
    m = agent_md_to_manifest(p, agent_id="wastlandqa")
    assert m["id"] == "wastlandqa" and m["tools_allowed"] == ["read_file", "run_in_terminal"]
    assert body.strip() == "# body"


def test_hive_role_json_converts(tmp_path):
    p = tmp_path / "router.json"
    p.write_text(json.dumps({"id": "router", "role": "Hive Router", "tags": ["hive", "router"],
                             "capabilities": ["task-routing"], "required_tools": ["read_file"],
                             "preferred_profile": "balanced"}), encoding="utf-8")
    m = hive_role_json_to_manifest(p)
    assert m["id"] == "router" and m["profile"] == "balanced" and "task-routing" in m["routing_tags"]


def test_registry_loads_agentx_hive_roles_md_and_catalog():
    reg = load_registry()
    assert not reg.errors, reg.errors[:3]
    for aid in ("overmind", "task_planner", "memory_summarizer", "game-qa-lead", "capability-guardian"):
        assert aid in reg.manifests, aid
    roles = {r["id"] for r in reg.hive_role_dicts()}
    assert {"router", "planner", "coder", "executor", "memory", "guardian", "governor"} <= roles


def test_hive_router_uses_agentx_loader():
    from realai.orchestration import hive_router

    agents = hive_router.load_github_hive_agents()
    assert agents and all(a.get("id") for a in agents)
    assert "router" in {a["id"] for a in agents}


def test_teams_load_validate_and_build_graphs():
    from realai.agentx.hive.teams import load_teams

    reg = load_registry()
    teams = load_teams(reg)
    assert {"vault77", "goon", "speedrouter", "guns-gear"} <= set(teams)
    for t in teams.values():
        assert t.validate() == [], t.validate()
        g = t.graph()
        assert t.lead in g.get_entrypoints()
    v = teams["vault77"]
    assert v.owner_for("fix the express api route").owner == "fullstack-dev"
    assert v.owner_for("anchor token wallet bug").owner == "vault-77-overseer"
    assert "wastlandqa" in reg.manifests  # converted from game-tester.md


def test_overmind_plans_routes_and_writes_hive_memory(tmp_path, monkeypatch):
    monkeypatch.setenv("REALAI_HOME", str(tmp_path))
    monkeypatch.delenv("REALAI_AGENTX_ALLOW_CLOUD", raising=False)
    from realai.agentx.hive.overmind import Overmind

    om = Overmind()
    out = om.run("Fix the express api route; then playtest the quest flow", team_id="vault77")
    assert [s["agent"] for s in out["steps"]] == ["fullstack-dev", "wastlandqa"]
    assert all(s["provider"] in {"local", "realai"} for s in out["steps"])
    assert all(s["profile"] == "safe" for s in out["steps"])
    assert out["memory"].get("ok")


def test_cloud_providers_off_by_default(monkeypatch):
    monkeypatch.delenv("REALAI_AGENTX_ALLOW_CLOUD", raising=False)
    from realai.agentx.providers.router import ProviderRouter

    assert set(ProviderRouter()._providers) == {"realai", "local"}


def test_guardian_defaults_to_safe_and_blocks_writes():
    from realai.agentx.hive.governance import CapabilityGuardian

    g = CapabilityGuardian()
    d = g.check({"id": "x", "tools_allowed": ["read_file", "apply_patch"]})
    assert d.profile == "safe" and not d.ok and "apply_patch" in d.missing and not d.can_write
    assert g.recommend(["read_file", "apply_patch"]) == "balanced"


@pytest.fixture()
def ws(tmp_path, monkeypatch):
    monkeypatch.setenv("REALAI_WORKSPACE", str(tmp_path))
    # approval-gated edits use the workspace tools' root + allowlist (Security #210 MED 6)
    monkeypatch.setenv("REALAI_TOOLS_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("REALAI_TOOLS_ALLOW", "workspace_write")
    monkeypatch.setenv("REALAI_APPROVALS_STORE", str(tmp_path / ".approvals.json"))
    monkeypatch.setenv("APPROVALS_STORE", str(tmp_path / ".approvals.json"))
    monkeypatch.delenv("REALAI_APPROVALS_AUDIT", raising=False)
    (tmp_path / "README.md").write_text("hello world\n", encoding="utf-8")
    return tmp_path


def test_patch_gate_requires_profile_approval_and_sandbox(ws):
    from realai.agentx.hive.governance import PatchGate

    calls = []
    gate = PatchGate(sandbox=lambda item: calls.append(item) or {"ok": True})
    assert gate.propose({"id": "ro"}, "README.md", "hello", "bye")["status"] == "denied"
    writer = {"id": "coder", "profile": "balanced"}
    req = gate.propose(writer, "README.md", "hello", "bye")
    assert req["status"] == "pending"
    assert gate.apply(req["approval_id"])["ok"] is False  # not approved yet
    assert (ws / "README.md").read_text() == "hello world\n"
    gate.gate.set_status(req["approval_id"], "approved", by="travis")
    assert gate.apply(req["approval_id"])["ok"] is True and calls
    assert (ws / "README.md").read_text() == "bye world\n"


def test_patch_gate_fails_closed_without_sandbox(ws, monkeypatch):
    monkeypatch.delenv("REALAI_SANDBOX_CMD", raising=False)
    from realai.agentx.hive.governance import PatchGate

    gate = PatchGate()
    req = gate.propose({"id": "coder", "profile": "balanced"}, "README.md", "hello", "bye")
    gate.gate.set_status(req["approval_id"], "approved", by="travis")
    out = gate.apply(req["approval_id"])
    assert out["ok"] is False and "sandbox" in out["reason"]
    assert (ws / "README.md").read_text() == "hello world\n"


def test_playtest_findings_go_to_owner_on_bus():
    from realai.agent_runtime.agent_runtime import MessageBus
    from realai.agentx.hive.playtest import PlaytestLoop
    from realai.agentx.hive.teams import load_teams

    team = load_teams(load_registry())["vault77"]
    bus = MessageBus()
    loop = PlaytestLoop(team=team, bus=bus)
    res = loop.run([{"id": "quest-xp", "area": "quest", "input": "quest xp", "check": lambda c: (False, "xp not granted")},
                    {"id": "ok", "area": "qa", "input": "x", "check": lambda c: (True, "")}])
    assert res["failed"] == 1
    inbox = bus.get_messages("wasteland-assistant")
    assert inbox and inbox[0].content["event"] == "qa.finding"
    assert bus.get_messages("wastlandqa")  # reviewer cc
    assert loop.run()["total"] >= 1  # harness cases from data/teams/vault77/playtests
