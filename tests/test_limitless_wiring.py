"""Tests for the limitless client wiring: local chat endpoint, web3 safety,
keyless web parsing, math/data abilities, and honest client labels."""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest import mock

import pytest


# --------------------------------------------------------------- stub LLM
class _Stub(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        if self.path.endswith("/embeddings"):
            inp = body.get("input") or []
            data = {"data": [{"embedding": [0.1, 0.2, 0.3], "index": i} for i, _ in enumerate(inp)], "model": "stub-embed"}
        else:
            last = (body.get("messages") or [{}])[-1].get("content", "")
            data = {"id": "stub-1", "model": "stub-llm",
                    "choices": [{"message": {"role": "assistant", "content": "STUB: " + last[:40] + "\n```python\nprint(1)\n```"}}]}
        out = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    def log_message(self, *a):
        pass


@pytest.fixture()
def stub_llm(monkeypatch):
    srv = HTTPServer(("127.0.0.1", 0), _Stub)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    monkeypatch.setenv("REALAI_CHAT_URL", f"http://127.0.0.1:{srv.server_port}/v1")
    yield srv
    srv.shutdown()


@pytest.fixture()
def no_llm(monkeypatch):
    monkeypatch.setenv("REALAI_CHAT_URL", "http://127.0.0.1:9/v1")
    monkeypatch.setattr("realai.local_media._DEFAULT_CHAT_BASES", ())


# --------------------------------------------------------------- endpoint
def test_chat_url_candidates_order(monkeypatch):
    from realai.local_media import chat_url_candidates

    monkeypatch.setenv("REALAI_CHAT_URL", "http://127.0.0.1:8081")
    monkeypatch.setenv("REALAI_LLM_BASE_URL", "http://127.0.0.1:9999/v1")
    urls = chat_url_candidates()
    assert urls[0] == "http://127.0.0.1:8081/v1/chat/completions"
    assert urls[1] == "http://127.0.0.1:9999/v1/chat/completions"
    assert urls[-2:] == ["http://127.0.0.1:8001/v1/chat/completions", "http://127.0.0.1:8080/v1/chat/completions"]


def test_hive_chat_unreachable_does_not_raise(no_llm):
    from realai.local_media import hive_chat

    out = hive_chat("hi", system="s")
    assert out["ok"] is False and out["tried"]


def test_hive_chat_uses_stub(stub_llm):
    from realai.local_media import hive_chat

    out = hive_chat("hello", system="s")
    assert out["ok"] and out["text"].startswith("STUB:") and out["model"] == "stub-llm"


def test_translation_ability_via_stub(stub_llm):
    from abilities.translation import run

    out = run("No limits", {"target": "es"})
    assert out["ok"] and out["translation"].startswith("STUB:")


# --------------------------------------------------------------- web3
def test_web3_and_secure_tools_import():
    import abilities.secure_tools  # noqa: F401
    from abilities.web3_integration import get_web3_tool

    tool = get_web3_tool()
    assert "solana" in tool.registry.backends


def test_web3_send_blocked_by_default(monkeypatch):
    from abilities.web3_integration import run

    monkeypatch.delenv("REALAI_WEB3_ALLOW_SEND", raising=False)
    for m in ("send", "sendTransaction", "eth_sendRawTransaction"):
        out = run(context={"method": m, "transaction": "AAAA", "approved": True})
        assert out["status"] == "blocked" and out["ok"] is False


def test_web3_send_needs_env_and_approval(monkeypatch):
    from abilities.web3_integration import run

    monkeypatch.setenv("REALAI_WEB3_ALLOW_SEND", "1")
    assert run(context={"method": "send", "transaction": "AAAA"})["status"] == "blocked"
    assert run(context={"method": "send", "approved": True})["status"] == "blocked"  # no signed tx


def test_web3_unknown_method_blocked():
    from abilities.web3_integration import run

    assert run(context={"method": "setAuthority"})["status"] == "blocked"


def test_web3_read_defaults_to_solana(monkeypatch):
    from abilities.web3_integration import run

    class R:
        def raise_for_status(self):
            pass

        def json(self):
            return {"jsonrpc": "2.0", "result": {"value": 1234}}

    with mock.patch("requests.post", return_value=R()) as post:
        out = run(context={"method": "getBalance", "address": "11111111111111111111111111111111"})
    assert out["ok"] and out["chain"] == "solana" and out["result"]["result"]["value"] == 1234
    assert post.call_args.kwargs["json"]["method"] == "getBalance"


def test_web3_tool_rejects_raw_send():
    from abilities.web3_integration import get_web3_tool

    with pytest.raises(PermissionError):
        get_web3_tool()(backend="solana", method="sendTransaction", params={})


# --------------------------------------------------------------- web parsing (offline)
DDG = '''<div class="result"><a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.org%2Fa">Alpha <b>A</b></a>
<a class="result__snippet">first snippet</a></div>
<div class="result"><a class="result__a" href="https://example.net/b">Beta</a></div>'''


def test_parse_ddg():
    from realai.core.tools.web import parse_ddg_html

    res = parse_ddg_html(DDG, 5)
    assert res[0]["url"] == "https://example.org/a" and "Alpha" in res[0]["title"]
    assert res[1]["url"] == "https://example.net/b"


def test_parse_arxiv_and_rss():
    from realai.core.tools.web import parse_arxiv, parse_feed

    atom = ('<feed xmlns="http://www.w3.org/2005/Atom"><entry><id>http://arxiv.org/abs/1</id><title>T  1</title>'
            '<summary>S</summary><published>2026-01-01</published><author><name>A</name></author></entry></feed>')
    a = parse_arxiv(atom)
    assert a[0]["title"] == "T 1" and a[0]["authors"] == ["A"]
    rss = '<rss><channel><item><title>N</title><link>https://x.org/n</link><pubDate>d</pubDate></item></channel></rss>'
    assert parse_feed(rss)[0] == {"title": "N", "url": "https://x.org/n", "date": "d"}


def test_extract_page():
    from realai.core.tools.web import extract_page

    out = extract_page("<html><title>Hi</title><script>x</script><body><p>Hello world</p><a href='https://a.b'>l</a></body></html>")
    assert out["title"] == "Hi" and "Hello world" in out["text"] and "x" not in out["text"].split()


def test_web_search_ability_search(monkeypatch):
    from realai.core.tools import web
    from abilities.web_search import run

    monkeypatch.setattr(web, "_get", lambda url, params=None, timeout=10.0: DDG)
    out = run("anything")
    assert out["status"] == "success" and len(out["results"]) == 2


# --------------------------------------------------------------- math / data
def test_math_solver_quadratic_verified():
    pytest.importorskip("sympy")
    from abilities.math_solver import run

    out = run("Solve for x: 2x² + 3x - 5 = 0")
    assert out["ok"] and out["verified"]
    assert {s["solution"]["x"] for s in out["solutions"]} == {"-5/2", "1"}


def test_math_solver_system_integral_eval():
    pytest.importorskip("sympy")
    from abilities.math_solver import run

    assert run("x + y = 3; x - y = 1")["answer"] == "x = 2, y = 1"
    integ = run("integrate x^2")
    assert integ["verified"] and integ["answer"].startswith("x**3/3")
    assert run("2^10")["answer"] == "1024"


def test_data_analysis():
    from abilities.data_analysis import run

    out = run(context={"data": [1, 2, 3, 4, 5, 6, 7, 8, 9, 100]})
    st = out["statistics"]
    assert st["count"] == 10 and st["median"] == 5.5 and st["outliers"] == [100.0] and st["trend"] == "rising"
    rows = run(context={"data": [{"a": 1, "b": 2}, {"a": 2, "b": 4}, {"a": 3, "b": 6}]})
    assert rows["correlation"]["a~b"] == pytest.approx(1.0)


# --------------------------------------------------------------- client
def test_client_single_agents_class_has_run():
    from realai import _v1_client
    from realai import RealAIClient

    src = open(_v1_client.__file__, encoding="utf-8").read()
    assert src.count("    class Agents:") == 1
    assert hasattr(RealAIClient.Agents, "run") and hasattr(RealAIClient.Agents, "orchestrate")


def test_client_honest_without_model(no_llm):
    from realai import RealAIClient

    c = RealAIClient()
    emb = c.embeddings.create(input_text="RealAI")
    assert any(emb["data"][0]["embedding"])  # never all zeros
    assert emb["real"] in (True, False) and emb["status"] in {"success", "fallback"}
    img = c.audio.generate(text="hi")
    assert img.get("audio_url") is None or "example.com" not in str(img.get("audio_url"))
    assert c.tasks.order_groceries(items=["milk"])["status"] == "plan_only"
    assert c.web3.smart_contract(blockchain="ethereum", params={})["status"] == "blocked"
    tr = c.model.translate(text="No limits", target_language="es")
    assert tr["real"] is False and tr["status"] in {"template", "unavailable"}
    sci = c.science.explain(topic="entanglement")
    assert sci.get("status") != "success" or sci.get("real") is not False


def test_client_with_stub_model(stub_llm):
    from realai import RealAIClient

    c = RealAIClient()
    chat = c.chat.create(messages=[{"role": "user", "content": "hello"}])
    assert chat["choices"][0]["message"]["content"].startswith("STUB:")
    tr = c.model.translate(text="No limits", target_language="es")
    assert tr["real"] is True and tr["translated_text"].startswith("STUB:")
    code = c.model.generate_code(prompt="print one", language="python")
    assert code["code"] == "print(1)" and code["verification"]["syntax_ok"] is True
    emb = c.embeddings.create(input_text="x")
    assert emb["backend"] in {"local_http", "sentence-transformers"} and emb["real"] is True


def test_math_and_data_via_client():
    pytest.importorskip("sympy")
    from realai import RealAIClient

    c = RealAIClient()
    assert c.math.solve(problem="x^2 = 4")["verified"] is True
    assert c.data.analyze(data=[1, 2, 3])["statistics"]["mean"] == 2.0
