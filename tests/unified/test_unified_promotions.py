"""Tests for pieces promoted from RealAi-unified 763a4c2 (all opt-in, PARTIAL)."""
from __future__ import annotations

import os

import pytest


@pytest.fixture
def home(tmp_path, monkeypatch):
    for key in list(os.environ):
        if key.startswith("REALAI_"):
            monkeypatch.delenv(key, raising=False)
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "router.py").write_text("# TODO legacy placeholder\n", encoding="utf-8")
    monkeypatch.setenv("REALAI_HOME", str(tmp_path))
    return tmp_path


# --- synthetic organs -------------------------------------------------------

def test_synthetic_organs_blueprint_and_scans(home, tmp_path_factory):
    from modules.organs.synthetic_organs import SyntheticOrgansRuntime

    rt = SyntheticOrgansRuntime()
    org = rt.create_organism("alpha", "scout", "explore")
    assert org["blueprint"]["system_count"] > 40
    assert rt.get_organism(org["id"]) is org
    cur = rt.curate_curiosity()
    assert any(i["path"] == "pkg/router.py" for i in cur["items"])
    arc = rt.archeology()
    assert arc["artifacts"][0]["signals"] == ["todo", "placeholder", "legacy"]
    # Targets outside REALAI_HOME fall back to home (no escape).
    outside = tmp_path_factory.mktemp("outside")
    assert rt.archeology(target=str(outside))["target"] == str(home.resolve())


def test_synthetic_organs_not_auto_loaded():
    from modules.organs import hive

    assert "synthetic_organs" not in open(hive.__file__, encoding="utf-8").read()


# --- self evolving ----------------------------------------------------------

def test_self_evolving_defaults_to_dry_run(home):
    from realai.plugins.self_evolving import SelfEvolvingRuntime, evolve, register

    rt = SelfEvolvingRuntime()
    assert rt.dry_run is True
    out = evolve("please search the web", runtime=rt)
    assert out["generated_plugin"]["name"] == "web_research_plugin"
    assert out["state"]["dry_run"] is True
    assert not (home / ".realai").exists()
    assert register(None)["dry_run"] is True


def test_self_evolving_enabled_writes_only_under_home(home, monkeypatch, tmp_path_factory):
    from realai.plugins.self_evolving import SelfEvolvingRuntime, evolve

    monkeypatch.setenv("REALAI_SELF_EVOLVING", "1")
    rt = SelfEvolvingRuntime()
    evolve("plan a task", runtime=rt)
    assert (home / ".realai" / "self_evolving_state.json").is_file()
    with pytest.raises(ValueError):
        SelfEvolvingRuntime(state_path=tmp_path_factory.mktemp("x") / "s.json")


# --- tool router ------------------------------------------------------------

def test_tool_router_local_first():
    from realai.plugins.tool_router import ROUTER_PLUGINS, route

    out = route("read the file in this directory")
    assert out["provider"] == "local" and out["selected"] == "file_read"
    assert ROUTER_PLUGINS.evaluate("file_read", "x", provider="local") > ROUTER_PLUGINS.evaluate("file_read", "x", provider="openai")
    assert route("hello there")["selected"] is None


# --- workspace info ---------------------------------------------------------

def test_workspace_info_confined(home, tmp_path_factory):
    from realai.plugins.workspace_info import register, workspace_catalog

    class M:  # noqa: D401
        pass

    m = M()
    assert register(m)["status"] == "PARTIAL"
    info = m.workspace_info(include_files=True)
    assert info["ok"] and "pkg" in info["entries"]
    assert workspace_catalog()["highlights"][0]["path"] == "pkg/router.py"
    outside = str(tmp_path_factory.mktemp("outside"))
    assert m.workspace_info(path=outside)["ok"] is False
    assert workspace_catalog(outside)["ok"] is False


# --- opt-in wiring ----------------------------------------------------------

def test_new_plugins_not_first_party():
    from realai.plugins import FIRST_PARTY, load_first_party

    for name in ("self_evolving", "tool_router", "workspace_info"):
        assert name not in FIRST_PARTY
        assert callable(load_first_party(name).register)


def test_catalog_rows_partial():
    from realai.ability_catalog import RUNDOWN_ABILITIES

    rows = {r["id"]: r for r in RUNDOWN_ABILITIES}
    for rid in ("synthetic_organs_runtime", "self_evolving", "tool_router_plugins", "workspace_info"):
        assert rows[rid]["status"] == "PARTIAL"


def test_unified_routes_off_by_default(home):
    from realai.server import unified_routes

    assert unified_routes.dispatch("POST", "/v1/tools/route", {"text": "search"}) is None


def test_unified_routes_opt_in(home, monkeypatch):
    from realai.server import unified_routes as ur

    monkeypatch.setenv("REALAI_UNIFIED_ROUTES", "1")
    code, body, _ = ur.dispatch("POST", "/v1/tools/route", {"text": "search the web"})
    assert code == 200 and body["selected"] == "web_search"
    code, body, _ = ur.dispatch("POST", "/v1/self/evolve", {"text": "read file"})
    assert code == 200 and body["self_evolution"]["state"]["dry_run"] is True
    code, body, _ = ur.dispatch("POST", "/v1/synthetic/organisms", {"name": "a", "species": "b"})
    assert code == 200
    oid = body["organism"]["id"]
    assert ur.dispatch("GET", f"/v1/synthetic/organisms/{oid}")[0] == 200
    assert ur.dispatch("GET", "/v1/synthetic/organisms/nope")[0] == 404
    assert ur.dispatch("POST", "/v1/workspace/catalog", {})[0] == 200
    assert ur.dispatch("POST", "/v1/self/evolve", {})[0] == 400
    assert ur.dispatch("GET", "/v1/unknown") is None
