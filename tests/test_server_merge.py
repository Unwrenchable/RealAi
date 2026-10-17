"""Server merge (decision 1): one canonical legacy API in realai/server, shims, opt-in bridge, local SDXL."""
from __future__ import annotations

import importlib

import pytest

pytest.importorskip("pydantic")


def test_shims_alias_canonical_legacy_api():
    canon = importlib.import_module("realai.server.legacy_api")
    for old in ("realai.api_server", "realai.core.api_server", "realai.plugins.api_server", "realai.plugins.api_big_server"):
        mod = importlib.import_module(old)
        assert mod is canon, old
    assert canon.RealAIAPIHandler.do_POST and callable(canon._vulkan_healthy) and callable(canon._looks_like_local_placeholder)
    assert canon._REPO_ROOT.joinpath("realai", "server", "legacy_api.py").is_file()
    src = open(canon.__file__, encoding="utf-8").read()
    assert "'/v1/memory/recall'" in src and "def _log_request_row" in src


def test_router_default_unchanged(monkeypatch):
    monkeypatch.delenv("REALAI_SERVER_MERGED_ROUTES", raising=False)
    monkeypatch.delenv("REALAI_IMAGES_LOCAL_SDXL", raising=False)
    router = pytest.importorskip("realai.server.router")
    status, data, _ = router.dispatch_request("GET", "/ui/providers")
    assert status == 404
    status, data, _ = router.dispatch_request("POST", "/v1/images/generations", {"prompt": "cat"})
    assert status == 200 and data["data"][0]["url"].startswith("https://realai.local/generated/")


def test_router_merged_routes_opt_in(monkeypatch):
    router = pytest.importorskip("realai.server.router")
    monkeypatch.setenv("REALAI_SERVER_MERGED_ROUTES", "1")
    status, data, ctype = router.dispatch_request("GET", "/ui/providers")
    assert status == 200 and ctype.startswith("application/json") and data and data[0]["id"] == "openai"
    status, data, _ = router.dispatch_request("GET", "/health")  # structured route still wins
    assert status == 200
    status, _, _ = router.dispatch_request("GET", "/v1/definitely-not-a-route")
    assert status == 404


def test_local_sdxl_images_opt_in(monkeypatch):
    router = pytest.importorskip("realai.server.router")
    from realai import local_sdxl

    monkeypatch.setattr(local_sdxl, "weights_present", lambda *a, **k: True)
    monkeypatch.setattr(local_sdxl, "handle_images_generations",
                        lambda p: {"created": 1, "data": [{"b64_json": "AAA"}], "backend": "sdxl_turbo_local"})
    monkeypatch.setenv("REALAI_IMAGES_LOCAL_SDXL", "1")
    status, data, _ = router.dispatch_request("POST", "/v1/images/generations", {"prompt": "pool table"})
    assert status == 200 and data["backend"] == "sdxl_turbo_local"
    from realai.server import legacy_api

    assert legacy_api._local_sdxl_enabled() is True
    monkeypatch.setenv("REALAI_IMAGES_LOCAL_SDXL", "0")
    assert legacy_api._local_sdxl_enabled() is False


def test_local_sdxl_module_is_local_only():
    from realai import local_sdxl

    src = open(local_sdxl.__file__, encoding="utf-8").read()
    assert "api_key" not in src.lower() and "xai" not in src.lower()
    assert local_sdxl._parse_size("4096x100") == (1024, 256)


def test_app_logger_defined():
    app = pytest.importorskip("realai.server.app")
    assert app.logger is not None
