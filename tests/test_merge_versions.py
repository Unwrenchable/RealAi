"""Version-family merges (docs/MERGE_LEDGER.md, 2026-10-16): pieces recovered from other development phases."""
import importlib


def test_agent_runtime_publishes_stages_to_shared_bus():
    from agents.agent_runtime import MESSAGE_BUS, MultiAgentPipeline

    out = MultiAgentPipeline().run("plan a 9-ball drill")
    msgs = MESSAGE_BUS.get_messages("orchestrator", limit=len(MultiAgentPipeline.STAGES))
    assert out["message_bus_id"] == id(MESSAGE_BUS)
    assert [m.content["stage"] for m in msgs] == MultiAgentPipeline.STAGES
    assert all(m.metadata.get("task") == "plan a 9-ball drill" for m in msgs)


def test_agent_runtime_bus_failure_never_breaks_pipeline(monkeypatch):
    from agents import agent_runtime as ar

    monkeypatch.setattr(ar.MESSAGE_BUS, "send", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("bus down")))
    out = ar.MultiAgentPipeline().run("x")
    assert set(ar.MultiAgentPipeline.STAGES) <= set(out.get("stages") or out.get("stage_outputs") or out)


def test_agent_tools_registry_recommend_profile_recovered():
    from agent_tools import registry as r

    agents, profiles = r.load_agents(), r.load_profiles()
    ag = next(iter(agents.values()))
    prof = r.recommend_profile(ag, profiles)
    assert prof.name in profiles
    assert r.assess_agent_access(ag, prof)["profile"] == prof.name


def test_rackup_money_abilities_carry_read_only_metadata():
    for ab in ("ledger_audit", "money_anomaly", "payout_sanity"):
        m = importlib.import_module(f"realai.plugins.rackup_coach.abilities.{ab}")
        assert m.ABILITY["id"] == ab and m.ABILITY["read_only"] is True and m.ABILITY["authorize_payout"] is False
        assert m.ABILITY["source"] == f"realai.plugins.rackup_coach.abilities.{ab}"


def test_orchestrator_recovered_read_only_tool_names():
    import realai.orchestration.v3_orchestrator as v

    assert v._run_tool("agent_info", {"agent_id": "definitely-missing"})["error"] == "agent_not_found"
    assert "entries" in v._run_tool("list_dir", {"target_directory": "abilities"})
    assert v._run_tool("read_file", {"target_file": "README.md", "limit": 2}).get("content")
    readme = open("README.md", "rb").read()
    out = v._run_tool("search_replace", {"file_path": "README.md", "old_string": "a", "new_string": "b"})
    assert out.get("error") and open("README.md", "rb").read() == readme  # write tool from that phase not merged
