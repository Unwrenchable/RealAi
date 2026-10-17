"""Next-run self_data fixes: text tool-call parsing, math_solver robustness, fair fact checks, hf dtype kwarg."""
import pytest

from realai.hive_tools.tool_loop import parse_tool_calls, run

K = {"math_solver", "list_agents", "request_approval"}


@pytest.mark.parametrize("content,name,args", [
    ('{"name": "math_solver", "arguments": {"problem": "x+1=2"}}', "math_solver", {"problem": "x+1=2"}),
    ('```json\n{"name":"math_solver","arguments":{"problem":"x"}}\n```', "math_solver", {"problem": "x"}),
    ('{{"name": "list_agents", "arguments": {{"query": "tax"}}}}', "list_agents", {"query": "tax"}),
    ('<function_call>{"name":"list_agents","parameters":{"query":"tax"}}</function_call>', "list_agents", {"query": "tax"}),
    ('<|python_tag|>{"name": "math_solver", "parameters": {"problem": "2+2"}}', "math_solver", {"problem": "2+2"}),
    ('<tool_call>{"name": "math_solver", "arguments": {"problem": "1"}}</tool_call>', "math_solver", {"problem": "1"}),
    ('{"type": "function", "function": {"name": "list_agents", "arguments": "{\\"query\\": \\"x\\"}"}}', "list_agents", {"query": "x"}),
])
def test_text_tool_calls_parse(content, name, args):
    out = parse_tool_calls({"content": content}, K)
    assert [(c["name"], c["arguments"]) for c in out] == [(name, args)]


def test_text_list_of_calls_and_action_alias():
    out = parse_tool_calls({"content": '[{"name":"math_solver","arguments":{"problem":"1"}},'
                                       '{"name":"list_agents","arguments":{}}]'}, K)
    assert [c["name"] for c in out] == ["math_solver", "list_agents"]
    out = parse_tool_calls({"content": '{"name": "run_terminal_command", "arguments": {"command": "git status"}}'}, K)
    assert out[0]["name"] == "request_approval" and out[0]["arguments"]["action"] == "run_terminal_command"


@pytest.mark.parametrize("content", ['The answer is {"name": "Bob", "age": 3}', '{"name":"rm_rf","arguments":{}}',
                                     "plain text", '{"name": "math_solver", "arguments": {"problem": <expr>}}'])
def test_text_fallback_rejects_non_calls(content):
    assert parse_tool_calls({"content": content}, K) == []


def test_structured_calls_win():
    msg = {"content": '{"name": "list_agents", "arguments": {}}',
           "tool_calls": [{"function": {"name": "math_solver", "arguments": '{"problem": "1+1"}'}}]}
    assert [c["name"] for c in parse_tool_calls(msg, K)] == ["math_solver"]


def test_run_executes_text_call_then_answers():
    pytest.importorskip("sympy")
    replies = iter([{"content": '```json\n{"name": "math_solver", "arguments": {"problem": "3x + 4 = 19"}}\n```'},
                    {"content": "x = 5"}])
    tools = [{"type": "function", "function": {"name": "math_solver", "parameters": {}}}]
    res = run(lambda m, t: next(replies), [{"role": "user", "content": "solve"}], tools=tools, offline=True)
    assert res["calls"][0]["result"]["answer"] == "x = 5" and res["answer"] == "x = 5"


@pytest.mark.parametrize("q,expect", [
    ("Compute the integral of 1/(x^2 + 4) dx from 0 to infinity.", "pi/4"),
    ("Integrate 1/(x**2 + 4) from x=0 to x=infinity", "pi/4"),
    ("Verify if the equation 2(x + 3) = 2x + 6 is always true.", "true for all values (identity)"),
    ("Find the average of 540, 520, 500, and 520", "520"),
    ("Solve the system of equations: x + y = 5 and x - y = 1", "x = 3, y = 2"),
    ("Solve 3x + 4 = 19 for x.", "x = 5"),
    ("What is the derivative of x**3 + 2*x?", "3*x**2 + 2"),
    ("x^2 - 5x + 6 = 0", "x = 2; x = 3"),
    ("Is (a+b)^2 = a^2+b^2 always true?", "not an identity: lhs - rhs = 2*a*b"),
])
def test_math_solver_natural_language(q, expect):
    pytest.importorskip("sympy")
    from realai import hive_tools

    r = hive_tools.execute("math_solver", {"problem": q})
    assert r["ok"] and r["answer"] == expect, r


def test_math_solver_points_stats_to_data_analysis_and_explains_parse_errors():
    pytest.importorskip("sympy")
    from realai import hive_tools

    r = hive_tools.execute("math_solver", {"problem": "What are the mean, median and standard deviation of 7, 68, 87, 43, 9?"})
    assert not r["ok"] and "data_analysis" in r["error"]
    r = hive_tools.execute("math_solver", {"problem": "+6: Minor piece pressure versus central pawn center"})
    assert not r["ok"] and "sympy-style" in r["error"]


def test_rating_preview_zero_rating_is_a_clear_error():
    from realai import hive_tools

    r = hive_tools.execute("rating_update_preview", {"player_rating": 92, "opponent_rating": 0, "won": True})
    assert not r["ok"] and "positive" in r["error"]


def test_fact_hit_fairness():
    from realai.training.self_data.verify import _norm, fact_hit

    assert fact_hit("provisional_slipping", _norm("Your rating is provisional and slipping."))
    assert not fact_hit("provisional_slipping", _norm("It is slipping."))
    assert fact_hit(["gold", "memory"], _norm("Routes: gold, memory."))
    assert not fact_hit(["gold", "nests"], _norm("Routes: gold, memory."))


def test_self_heal_and_routes_facts_accept_fair_answers():
    from realai import hive_tools
    from realai.training.self_data.verify import _norm, fact_hit

    sh = {"enabled": False, "artifacts_present": 12, "artifacts_total": 27, "missing": ["a"] * 15}
    groups = hive_tools.key_facts("self_heal_status", sh, {})
    assert any(fact_hit(g, _norm("Self-heal is not enabled; 15 artifacts are missing.")) for g in groups[0])
    hr = {"route_count": 3, "routes": ["gold", "memory", "nests"], "hive_agents": []}
    groups = hive_tools.key_facts("hive_routes_status", hr, {})
    assert any(fact_hit(g, _norm("The router knows gold, memory and nests.")) for g in groups[0])


def test_agent_named_by_role_counts():
    from realai.training.self_data import verify as v

    calls = [{"name": "route_to_agent", "arguments": {"agent": "tax-strategist", "task": "t"},
              "result": {"ok": True, "handoff": {"agent": "tax-strategist", "role": "Tax Strategist", "task": "t",
                                                  "status": "planned (dry run)"}}}]
    msgs = [{"role": "user", "content": "Who handles my taxes?"}]
    _, why = v.verify(msgs + [{"role": "assistant", "content": "Routed to the Tax Strategist agent (dry-run plan)."}], calls)
    assert "agent_not_named" not in why
    _, why = v.verify(msgs + [{"role": "assistant", "content": "Routed to an agent (dry-run plan)."}], calls)
    assert "agent_not_named" in why


def test_request_approval_spec_exposes_script_code():
    from realai import hive_tools

    props = hive_tools.SPECS["request_approval"]["function"]["parameters"]["properties"]
    assert "code" in props
    r = hive_tools.execute("request_approval", {"action": "run_script", "reason": "t", "code": "print(1)"}, offline=True)
    assert r["status"] == "pending" and r["executed"] is False


@pytest.mark.parametrize("v,kw", [("4.44.2", "torch_dtype"), ("4.46.3", "torch_dtype"), ("4.55.4", "torch_dtype"),
                                  ("4.56.0.dev0", "dtype"), ("4.56.2", "dtype"), ("5.1.0", "dtype")])
def test_dtype_kw_by_version(v, kw):
    from realai.training.hf_compat import dtype_kwargs

    assert list(dtype_kwargs("fp", v)) == [kw]
