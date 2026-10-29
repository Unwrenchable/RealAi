"""Read-only routing endpoints recovered from origin/RealAi-unified (off by default)."""
from realai.server.router import dispatch_request


def test_routing_routes_defaults(monkeypatch):
    monkeypatch.delenv("REALAI_ROUTING_ROUTES", raising=False)
    monkeypatch.delenv("REALAI_UNIFIED_ROUTES", raising=False)
    monkeypatch.delenv("REALAI_SERVER_MERGED_ROUTES", raising=False)
    monkeypatch.delenv("REALAI_TOOLS_ROUTE", raising=False)
    assert dispatch_request("POST", "/v1/providers/route", {})[0] == 404  # still opt-in
    code, body, _ = dispatch_request("POST", "/v1/tools/route", {"text": "search the web"})
    assert code == 200 and body["selected"] == "web_search" and body["routing"]["executes"] is False
    monkeypatch.setenv("REALAI_TOOLS_ROUTE", "0")  # opt out
    assert dispatch_request("POST", "/v1/tools/route", {"text": "search the web"})[0] == 404


def test_tool_route_selects_and_chains_without_executing(monkeypatch):
    monkeypatch.setenv("REALAI_ROUTING_ROUTES", "1")
    from realai.server import tools_runtime

    before = list(tools_runtime.TOOLS.list_audit())
    code, body, _ = dispatch_request(
        "POST", "/v1/tools/route", {"text": "search the latest news", "chain": True, "max_tools": 1}
    )
    assert code == 200 and body["selected"] == "web_search"
    assert body["routing"]["selected"]["name"] == "web_search" and body["routing"]["executes"] is False
    assert body["routing"]["chain"] == [{"name": "file_read", "reason": "local context first"}]
    assert list(tools_runtime.TOOLS.list_audit()) == before  # nothing executed / audited

    code, body, _ = dispatch_request("POST", "/v1/tools/route", {"text": "zzz", "allowed_tools": ["file_read"]})
    assert code == 200 and body["selected"] == "file_read" and body["routing"]["reason"].startswith("fallback")
    assert dispatch_request("POST", "/v1/tools/route", {})[0] == 400
    assert dispatch_request("GET", "/v1/tools/route")[0] == 404


def test_provider_route_reports_routing(monkeypatch):
    monkeypatch.setenv("REALAI_ROUTING_ROUTES", "1")
    from realai.server.config import list_models

    model = list_models()[0]
    code, body, _ = dispatch_request("POST", "/v1/providers/route", {"model": model})
    assert code == 200 and body["model"] == model
    assert set(body["routing"]) >= {"provider", "backend", "type", "health", "capabilities", "selected"}
    assert dispatch_request("POST", "/v1/providers/route", {"model": "no-such-model-xyz"})[0] == 404
    assert dispatch_request("POST", "/v1/tools/execute", {"name": "file_read"})[0] == 404  # never recovered
