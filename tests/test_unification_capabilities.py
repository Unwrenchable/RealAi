import os
import tempfile

from realai.server.config import load_registry
from realai.server.router import dispatch_request
from realai.server.tools_runtime import ToolManifest, TOOLS


def _call(path, method="GET", payload=None):
    return dispatch_request(method, path, payload)


def test_memory_store_inspect_and_clear_round_trip(tmp_path, monkeypatch):
    db_path = tmp_path / "unified-memory.sqlite3"
    monkeypatch.setenv("REALAI_SERVER_DB_PATH", str(db_path))
    os.environ["REALAI_SERVER_DB_PATH"] = str(db_path)

    status, body, _ = _call(
        "/v1/memory/store",
        method="POST",
        payload={"user_id": "u1", "agent_id": "a1", "content": "remember this"},
    )
    assert status == 200
    assert body["status"] == "stored"

    status, body, _ = _call(
        "/v1/memory/inspect",
        method="POST",
        payload={"user_id": "u1", "agent_id": "a1"},
    )
    assert status == 200
    assert body["data"][0]["content"] == "remember this"

    status, body, _ = _call(
        "/v1/memory/clear",
        method="POST",
        payload={"user_id": "u1", "agent_id": "a1"},
    )
    assert status == 200
    assert body["deleted"] >= 1


def test_tool_runtime_supports_schema_validation_and_execution():
    manifest = ToolManifest(
        name="demo_tool",
        description="Demo tool",
        params={"query": "string"},
        permissions=["network"],
        timeout_ms=5000,
    )
    assert TOOLS.validate_manifest(manifest) is True

    result = TOOLS.execute("demo_tool", {"query": "hello"}, actor="tester")
    assert result["tool"] == "demo_tool"
    assert result["ok"] is True
    assert result["params"]["query"] == "hello"


def test_world_state_endpoints_expose_state_and_observations():
    status, body, _ = _call("/v1/world/state")
    assert status == 200
    assert "world" in body
    assert "facts" in body["world"]

    status, body, _ = _call(
        "/v1/world/observe",
        method="POST",
        payload={"content": "The city is alive", "source": "test"},
    )
    assert status == 200
    assert body["observed"] is True
    assert body["world"]["facts"]["city"] == "alive"


def test_workspace_info_plugin_builds_a_lightweight_catalog():
    from plugins.workspace_info_plugin import register

    class DummyModel:
        pass

    model = DummyModel()
    register(model)
    result = model.workspace_info(path="/workspaces/RealAi", include_files=True)

    assert result["ok"] is True
    assert result["path"].endswith("RealAi")
    assert result["catalog"] is not None
    assert result["catalog"]["summary"]["files_scanned"] > 0
    assert result["catalog"]["summary"]["highlight_count"] > 0
    assert result["catalog"]["highlights"]


def test_plugin_listing_and_execution_are_public():
    status, body, _ = _call("/v1/plugins")
    assert status == 200
    assert any(item["name"] == "sample_plugin" for item in body["data"])
    assert any(item["name"] == "workspace_info_plugin" for item in body["data"])

    status, body, _ = _call(
        "/v1/plugins/execute",
        method="POST",
        payload={"name": "sample_plugin", "data": {"hello": "world"}},
    )
    assert status == 200
    assert body["ok"] is True
    assert body["plugin"] == "sample_plugin"

    status, body, _ = _call(
        "/v1/plugins/execute",
        method="POST",
        payload={"name": "workspace_info_plugin", "data": {"path": "/workspaces/RealAi"}},
    )
    assert status == 200
    assert body["ok"] is True
    assert body["plugin"] == "workspace_info_plugin"
    assert body["metadata"]["capabilities"]


def test_tool_execution_endpoint_is_public():
    status, body, _ = _call(
        "/v1/tools/execute",
        method="POST",
        payload={"name": "file_read", "params": {"path": "/tmp"}, "actor": "tester"},
    )
    assert status == 200
    assert body["ok"] is True
    assert body["tool"] == "file_read"
    assert body["result"]["tool"] == "file_read"


def test_tool_routing_endpoint_selects_best_tool():
    status, body, _ = _call(
        "/v1/tools/route",
        method="POST",
        payload={"text": "Please search the web for the latest AI news", "allowed_tools": ["web_search", "file_read", "web3_solana_rpc"]},
    )
    assert status == 200
    assert body["ok"] is True
    assert body["routing"]["selected"]["name"] == "web_search"


def test_tool_routing_uses_provider_preferences_and_chains_tools():
    status, body, _ = _call(
        "/v1/tools/route",
        method="POST",
        payload={
            "text": "Read the project file and then search the web for the latest AI news",
            "allowed_tools": ["web_search", "file_read", "web3_solana_rpc"],
            "provider": "local",
            "chain": True,
            "max_tools": 2,
        },
    )
    assert status == 200
    assert body["ok"] is True
    assert body["routing"]["provider"] == "local"
    assert any(item["name"] == "file_read" for item in body["routing"]["chain"])
    assert any(item["name"] == "web_search" for item in body["routing"]["chain"])


def test_self_evolution_endpoint_generates_diagnostics_and_plugins():
    status, body, _ = _call(
        "/v1/self/evolve",
        method="POST",
        payload={"text": "Please search the web and plan the next steps", "tool_name": "web_search"},
    )
    assert status == 200
    assert body["ok"] is True
    assert body["self_evolution"]["diagnosis"]["concerns"]
    assert body["self_evolution"]["generated_plugin"]["name"]


def test_skill_and_agent_discovery_endpoints_are_public():
    status, body, _ = _call("/v1/skills")
    assert status == 200
    assert body["object"] == "list"
    assert any(item["name"] == "planner" for item in body["data"])

    status, body, _ = _call("/v1/agents")
    assert status == 200
    assert body["object"] == "list"
    assert any(item["name"] == "planner" for item in body["data"])


def test_health_payload_reports_runtime_components():
    status, body, _ = _call("/health")
    assert status == 200
    runtime = body["runtime"]
    assert runtime["memory"]["enabled"] is True
    assert runtime["plugins"]["count"] >= 1
    assert runtime["world"]["enabled"] is True
    assert runtime["tools"]["count"] >= 1


def test_runtime_docs_are_generated_from_runtime():
    from pathlib import Path

    tools_doc = Path("tools.md")
    skills_doc = Path("skills.md")
    assert tools_doc.exists()
    assert skills_doc.exists()
    assert "web_search" in tools_doc.read_text(encoding="utf-8")


def test_reflection_synthesis_and_agent_orchestration_endpoints_work():
    status, body, _ = _call(
        "/v1/reflection/analyze",
        method="POST",
        payload={"text": "We are preparing a launch", "goal": "ship quickly"},
    )
    assert status == 200
    assert body["reflection"]["summary"]

    status, body, _ = _call(
        "/v1/synthesis/knowledge",
        method="POST",
        payload={"facts": ["A launch is planned", "The team is ready"]},
    )
    assert status == 200
    assert body["synthesis"]["summary"]

    status, body, _ = _call(
        "/v1/agents/orchestrate",
        method="POST",
        payload={"task": "prepare a launch", "agents": ["planner", "executor"]},
    )
    assert status == 200
    assert body["orchestration"]["task"] == "prepare a launch"


def test_provider_routing_endpoint_returns_selection_details():
    status, body, _ = _call(
        "/v1/providers/route",
        method="POST",
        payload={"model": "realai-1.0"},
    )
    assert status == 200
    assert body["model"] == "realai-1.0"
    assert body["routing"]["provider"]
    assert "health" in body["routing"]


def test_synthetic_organism_routes_create_list_and_read():
    status, body, _ = _call(
        "/v1/synthetic/organism",
        method="POST",
        payload={"name": "Nova", "species": "microbe", "prompt": "self-replicating explorer"},
    )
    assert status == 200
    assert body["ok"] is True
    assert body["organism"]["name"] == "Nova"
    blueprint = body["organism"]["blueprint"]
    assert blueprint["system_count"] == 44
    assert blueprint["cognitive_organs"][0]["name"] == "Frontal Cortex"
    assert blueprint["meta_layers"][0]["name"] == "Synthetic Intuition Layer"
    assert blueprint["behavioral_directives"][0] == "explore the device"
    assert blueprint["meta_systems"][0]["name"] == "Synthetic Intuition Layer"
    assert any(system["name"] == "Synthetic Soul Layer" for system in blueprint["systems"])
    assert any(system["name"] == "Synthetic Guardian Layer" for system in blueprint["systems"])
    assert any(directive == "maintain safety" for directive in blueprint["behavioral_directives"])

    status, body, _ = _call("/v1/synthetic/organisms")
    assert status == 200
    assert any(item["name"] == "Nova" for item in body["data"])

    organism_id = body["data"][0]["id"]
    status, body, _ = _call(f"/v1/synthetic/organisms/{organism_id}")
    assert status == 200
    assert body["data"]["id"] == organism_id


def test_curiosity_and_archeology_routes_return_scans():
    status, body, _ = _call(
        "/v1/curiosity",
        method="POST",
        payload={"target": "/workspaces/RealAi"},
    )
    assert status == 200
    assert body["ok"] is True
    assert body["items"]

    status, body, _ = _call(
        "/v1/archeology",
        method="POST",
        payload={"target": "/workspaces/RealAi"},
    )
    assert status == 200
    assert body["ok"] is True
    assert body["artifacts"]


def test_workspace_catalog_endpoint_returns_story_and_buckets():
    status, body, _ = _call(
        "/v1/workspace/catalog",
        method="POST",
        payload={"root": "/workspaces/RealAi"},
    )
    assert status == 200
    assert body["root"].endswith("RealAi")
    assert body["snapshot"]["files_considered"] > 0
    assert body["snapshot"]["top_weight"] >= 0
    assert body["story"]
    assert set(body["buckets"].keys()) == {"priority", "tests", "repair", "other"}


def test_native_default_model_is_local_first_and_public():
    from realai.server.config import load_settings

    settings = load_settings()
    assert settings.default_chat_model == "realai-native"
    registry = load_registry()
    assert "realai-native" in registry
