"""Round 3 generator fix: the 30B teacher gets typed rackup_invoke payloads + routing rules; saved rows don't."""
import json
import random

from realai import hive_tools
from realai.training.self_data import generate as G
from realai.training.self_data.filter import bad_payload


def test_teacher_specs_type_rackup_payload_only_for_teacher():
    t = {s["function"]["name"]: s for s in G.teacher_specs()}
    pl = t["rackup_invoke"]["function"]["parameters"]["properties"]["payload"]
    assert {"table_size", "skill_level", "from_system", "from_value", "my_score", "opp_score", "opponent_id", "discipline"} <= set(pl["properties"])
    assert pl["additionalProperties"] is False and "from_system" in t["rackup_invoke"]["function"]["description"]
    assert pl["properties"]["skill_level"] == {"type": "string", "enum": ["beginner", "intermediate", "advanced", "pro"]}
    assert pl["properties"]["table_size"]["enum"] == ["7ft", "9ft"] and pl["properties"]["from_value"]["type"] == "number"
    from realai.training.self_data.filter import VALUES
    for k, ok in VALUES.items():  # every enum value the teacher may emit passes filter v2
        assert set(pl["properties"][k]["enum"]) <= ok
    live = hive_tools.SPECS["rackup_invoke"]["function"]["parameters"]["properties"]["payload"]
    assert live == {"type": "object"}  # the live catalog is unchanged


def test_teacher_payload_keys_pass_filter_v2():
    for ab, keys in G.RACKUP_PAYLOADS.items():
        need = {k for k, v in keys.items() if "required" in v} or {k for k in keys if k != "won"}
        pl = {k: {"table_size": "7ft", "skill_level": "pro", "from_system": "apa", "discipline": "8-ball"}.get(k, 5) for k in need}
        assert bad_payload([{"name": "rackup_invoke", "arguments": {"ability": ab, "payload": pl}}]) is None, ab


def test_seeds_cover_core_rackup_kinds_and_security_agents():
    rng = random.Random(3)
    s = G.seeds("rackup_invoke", rng, 6)
    assert "Pyramid" in s and "APA" in s and "league match" in s
    seen = set()
    for i in range(20):
        seen |= {a for a in ("security-engineer", "cybersecurity-expert", "accessibility-auditor") if a in G.seeds("route_to_agent", random.Random(i), 6)}
    assert seen


def test_saved_rows_keep_plain_system_and_live_specs(tmp_path, monkeypatch):
    from realai.training.dataset_builder.adapters_tools import TOOL_SYSTEM

    monkeypatch.setenv("REALAI_HOME", str(tmp_path))
    seen = {}

    def chat(msgs, tools):
        if tools is None:
            return {"content": json.dumps(["How many points win Pyramid on a 7ft table for an advanced player?"])}
        seen["system"] = msgs[0]["content"]
        seen["payload"] = next(t for t in tools if t["function"]["name"] == "rackup_invoke")["function"]["parameters"]["properties"]["payload"]
        if msgs[-1]["role"] == "tool":
            r = json.loads(msgs[-1]["content"])
            return {"content": f"Race to {r['result']['config']['points_to_win']} points."}
        return {"content": "", "tool_calls": [{"function": {"name": "rackup_invoke", "arguments": json.dumps(
            {"ability": "pyramid_rules", "payload": {"table_size": "7ft", "skill_level": "advanced"}})}}]}

    s = G.run(chat, plan={"rackup_invoke": 1}, minutes=0.05, max_rows=1, log=lambda x: None, seed=1)
    assert s["accepted"] == 1
    assert "Routing rules" in seen["system"] and "properties" in seen["payload"]
    row = json.loads(open(s["accepted_file"]).read().splitlines()[0])
    assert row["messages"][0]["content"] == TOOL_SYSTEM
    rk = [t for t in row["tools"] if t["function"]["name"] == "rackup_invoke"]
    assert rk and rk[0]["function"]["parameters"]["properties"]["payload"] == {"type": "object"}
