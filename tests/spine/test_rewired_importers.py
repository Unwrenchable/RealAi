"""Spine 1b: importers rewired off archive-verdict orchestrator files still work.

Covers abilities/orchestration_surface.py (entry_shim, unified_blueprint),
realai/core_hive_router.py and realai/orchestration/v3_runtime_bridge.py (hive).
Parity checks against the old files are skipped once those files are archived.
"""
import importlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
REWIRED = ("abilities/orchestration_surface.py", "realai/core_hive_router.py",
           "realai/orchestration/v3_runtime_bridge.py")
GONE = ("realai.orchestration.realai_orchestrator", "realai.orchestration.unified_orchestrator",
        "abilities.hive_orchestrator")


@pytest.mark.parametrize("rel", REWIRED)
def test_no_string_refs_to_rewired_targets(rel):
    text = (ROOT / rel).read_text(encoding="utf-8")
    for mod in GONE:
        assert f'"{mod}"' not in text, f"{rel} still references {mod}"


def test_hive_router_ability_entrypoint():
    hr = importlib.import_module("realai.orchestration.hive_router")
    assert hr.ABILITY["id"] == "hive_orchestrator"
    out = hr.run(context={"action": "routes"})
    assert out["ok"] is True and out["ability"] == "hive_orchestrator"
    nest = hr.run(context={"action": "nest"})
    assert nest["ok"] is True and "nest" in nest


def test_hive_router_matches_old_wrapper():
    if not (ROOT / "abilities" / "hive_orchestrator.py").is_file():
        pytest.skip("abilities/hive_orchestrator.py archived")
    old = importlib.import_module("abilities.hive_orchestrator")
    hr = importlib.import_module("realai.orchestration.hive_router")
    for action in ("routes", "nest"):
        assert hr.run(context={"action": action}) == old.run(context={"action": action})


def test_core_hive_router_domain_route_resolves():
    chr_ = importlib.import_module("realai.core_hive_router")
    target = chr_.ROUTING_TABLE["domain"]
    assert target == "realai.orchestration.hive_router"
    assert callable(importlib.import_module(target).run)


@pytest.mark.parametrize("aid", ["hive_orchestrator", "hive"])
def test_bridge_ability_hive_dispatch(aid):
    br = importlib.import_module("realai.orchestration.v3_runtime_bridge")
    out = br.execute_registry_tool(f"ability.{aid}", {"context": {"action": "routes"}})
    assert out.get("ok") is True, out
    assert out.get("ability") == "hive_orchestrator"


def test_bridge_bare_hive_name_dispatch():
    br = importlib.import_module("realai.orchestration.v3_runtime_bridge")
    out = br.execute_registry_tool("hive_orchestrator", {"context": {"action": "routes"}})
    assert out.get("ok") is True and out.get("ability") == "hive_orchestrator", out


def test_entry_shim_points_at_core():
    s = importlib.import_module("abilities.orchestration_surface")
    meta = s.ORCH_REGISTRY["entry_shim"]
    assert meta["module"] == "realai.orchestration.v3_orchestrator"
    assert s._resolve("realai_orchestrator") == "entry_shim"
    assert s._resolve("v3") == "v3"


def _sample_manifest(tmp_path):
    p = tmp_path / "unify_manifest.json"
    p.write_text(json.dumps({"flows": {"orchestrators": ["a", "b"], "providers": ["p1", "p2"],
                                       "memory": [], "world": ["w"], "plugins": ["x"]}}), encoding="utf-8")
    return p


def test_unified_blueprint_inline(tmp_path):
    s = importlib.import_module("abilities.orchestration_surface")
    out = s._unified_blueprint(_sample_manifest(tmp_path))
    assert out["orchestrators"] == ["a", "b"] and out["provider"] == "p1"
    assert out["memory"] is None and out["world"] == "w" and out["plugins"] == ["x"]


def test_unified_blueprint_matches_old_class(tmp_path):
    f = ROOT / "realai" / "orchestration" / "unified_orchestrator.py"
    if not f.is_file():
        pytest.skip("unified_orchestrator.py archived")
    spec = importlib.util.spec_from_file_location("_old_unified", f)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    m = _sample_manifest(tmp_path)
    s = importlib.import_module("abilities.orchestration_surface")
    assert s._unified_blueprint(m) == mod.UnifiedOrchestrator(ROOT, m).build()


def test_unified_blueprint_runner_without_manifest():
    s = importlib.import_module("abilities.orchestration_surface")
    out = s._run_module("unified_blueprint")
    assert out["result"]["ok"] is True or "orchestrators" in out["result"]
