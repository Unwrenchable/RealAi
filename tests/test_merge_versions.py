"""Version-family merges (docs/MERGE_LEDGER.md, 2026-10-16): pieces recovered from other development phases."""
import importlib
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _canonical(rel: str, name: str):
    """Load the canonical file by path: some suites put realai/ on sys.path, where parked twins
    (realai/agents, ...) would shadow the product-root packages."""
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[name] = mod  # dataclasses need the module registered
    spec.loader.exec_module(mod)
    return mod


def test_agent_runtime_publishes_stages_to_shared_bus():
    ar = _canonical("agents/agent_runtime.py", "_merge_test_agent_runtime")
    MESSAGE_BUS, MultiAgentPipeline = ar.MESSAGE_BUS, ar.MultiAgentPipeline

    out = MultiAgentPipeline().run("plan a 9-ball drill")
    msgs = MESSAGE_BUS.get_messages("orchestrator", limit=len(MultiAgentPipeline.STAGES))
    assert out["message_bus_id"] == id(MESSAGE_BUS)
    assert [m.content["stage"] for m in msgs] == MultiAgentPipeline.STAGES
    assert all(m.metadata.get("task") == "plan a 9-ball drill" for m in msgs)


def test_agent_runtime_bus_failure_never_breaks_pipeline(monkeypatch):
    ar = _canonical("agents/agent_runtime.py", "_merge_test_agent_runtime2")

    monkeypatch.setattr(ar.MESSAGE_BUS, "send", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("bus down")))
    out = ar.MultiAgentPipeline().run("x")
    assert set(ar.MultiAgentPipeline.STAGES) <= set(out.get("stages") or out.get("stage_outputs") or out)


def test_agent_tools_registry_recommend_profile_recovered():
    import ast
    from types import SimpleNamespace as NS

    src = (ROOT / "agent_tools" / "registry.py").read_text(encoding="utf-8")
    fn = next(n for n in ast.parse(src).body if getattr(n, "name", "") == "recommend_profile")
    ns: dict = {}
    exec(compile(ast.Module([fn], []), "registry.py", "exec"), {"AgentDefinition": object, "AccessProfile": object}, ns)
    rec = ns["recommend_profile"]
    profiles = {"safe": NS(name="safe", tools=["fs"]), "balanced": NS(name="balanced", tools=["fs", "http"]),
                "power": NS(name="power", tools=["fs", "http", "shell"])}
    assert rec(NS(preferred_profile="power", required_tools=[]), profiles).name == "power"
    assert rec(NS(preferred_profile="none", required_tools=["http"]), profiles).name == "balanced"
    assert rec(NS(preferred_profile="none", required_tools=["gpu"]), profiles).name == "safe"


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
