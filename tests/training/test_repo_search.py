"""repo_search (tool 32): read-only, mirror root only, allowlist, ~4 KB cap, secret redaction, no writes."""
from __future__ import annotations

import json
import os

import pytest

from realai import hive_tools as H
from realai.hive_tools import repo_search as R

FAKE_TOKEN = "ghp_" + "Q7" * 18  # built at runtime: matches the github_token pattern, not a real credential


def _w(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


@pytest.fixture
def mirror(tmp_path, monkeypatch):
    root = tmp_path / "mirror"
    _w(root / "RealAi" / "realai" / "training" / "adapters_tools.py", "import random\n\ndef tool_subset(right, key):\n    return right\n")
    _w(root / "RealAi" / "realai" / "tools.py", "class ToolRegistry:\n    pass\n")
    _w(root / "Rack_em_up" / "README.md", "# RackUp\n\nPool league app.\n")
    _w(root / "Rack_em_up" / "src" / "rating.ts", "// Glicko-2 rating\nexport const k = 1;\n" + "\n".join(f"// line {i}" for i in range(400)))
    _w(root / "Rack_em_up" / "src" / "config.ts", f"const token = '{FAKE_TOKEN}';\nexport const apiKey = 'abcd1234efgh5678';\n")
    _w(root / "Rack_em_up" / ".env", "API_KEY=" + FAKE_TOKEN + "\n")
    _w(root / "Rack_em_up" / ".env.example", "API_KEY=\n")
    _w(root / "Rack_em_up" / "node_modules" / "x" / "index.js", "glicko vendored\n")
    _w(root / "Rack_em_up" / "flagged.ts", "flagged by the mirror scan\n")
    _w(root / "agent-tools" / "agent_tools" / "engine" / ".env", "X=" + FAKE_TOKEN + "\n")
    _w(root / "agent-tools" / "README.md", "# agent-tools\n")
    _w(root / "LustLink" / "README.md", "excluded\n")
    _w(root / "Token-scalper" / "scalper_bot.py", "def buy(): pass\n")
    (root / "Rack_em_up" / "big.md").write_text("glicko " * 200 + "\n" + ("y" * 190 + "\n") * 300, encoding="utf-8")
    _w(tmp_path / "outside.txt", "outside secret glicko\n")
    try:
        os.symlink(tmp_path / "outside.txt", root / "Rack_em_up" / "link.txt")
    except (OSError, NotImplementedError):
        pass
    (root / "repo_mirror_manifest.json").write_text(json.dumps(
        {"repos": {"Rack_em_up": {"commit": "abc123def4567890", "blocked": ["flagged.ts"]}}}), encoding="utf-8")
    monkeypatch.setenv("REALAI_REPO_MIRROR", str(root))
    return root


def X(**a):
    return H.execute("repo_search", a)


def test_registered_live_default_on_and_opt_out(monkeypatch):
    assert "repo_search" in H.SPECS and "repo_search" in H.CORE_TOOLS and "repo_search" not in H.NEW_TOOLS
    assert "repo_search" not in H.NETWORK_TOOLS and len(H.SPECS) == 32
    monkeypatch.delenv("REALAI_REPO_SEARCH", raising=False)
    for hive in ("", "1"):
        monkeypatch.setenv("REALAI_HIVE_TOOLS", hive)
        assert "repo_search" in {s["function"]["name"] for s in H.live_specs()}
    monkeypatch.setenv("REALAI_REPO_SEARCH", "0")
    for hive in ("", "1"):
        monkeypatch.setenv("REALAI_HIVE_TOOLS", hive)
        assert "repo_search" not in {s["function"]["name"] for s in H.live_specs()}


def test_confusable_hard_distractors():
    from realai.training.dataset_builder.adapters_tools import CONFUSABLE, tool_subset

    assert {"module_lookup", "plugin_lookup", "memory_search", "request_approval"} <= set(CONFUSABLE["repo_search"])
    assert "repo_search" in CONFUSABLE["module_lookup"] and "repo_search" in CONFUSABLE["memory_search"]
    for i in range(10):
        names = tool_subset(["repo_search"], f"k{i}")
        assert "repo_search" in names and len(set(names) & set(CONFUSABLE["repo_search"])) >= 2


def test_no_mirror(monkeypatch, tmp_path):
    monkeypatch.setenv("REALAI_REPO_MIRROR", str(tmp_path / "missing"))
    r = X(action="list")
    assert r["ok"] is False and "mirror" in r["error"]


def test_allowlist(mirror):
    r = X(action="list")
    names = [x["repo"] for x in r["repos"]]
    assert names == ["RealAi", "Rack_em_up", "agent-tools"] or set(names) == {"RealAi", "Rack_em_up", "agent-tools"}
    for bad in ("LustLink", "Token-scalper", "reverse-phone-search", "not-a-repo"):
        assert X(action="list", repo=bad)["ok"] is False
        assert X(action="read", repo=bad, path="README.md")["ok"] is False
    g = X(action="grep", query="buy")  # Token-scalper is mirrored here but never searched
    assert all(h["repo"] != "Token-scalper" for h in g.get("hits") or [])
    assert X(action="list", repo="rackup")["repo"] == "Rack_em_up"  # alias


@pytest.mark.parametrize("path", ["../outside.txt", "../../outside.txt", "/etc/passwd", "C:\\Windows\\win.ini", "C:/x",
                                  "..\\..\\outside.txt", "src/../../outside.txt", "~/.ssh/id_rsa", "//server/share/x"])
def test_path_escape(mirror, path):
    for action in ("read", "list", "grep"):
        r = X(action=action, repo="Rack_em_up", path=path, query="glicko")
        assert r["ok"] is False
        assert "outside secret" not in json.dumps(r)


def test_symlink_out_of_repo_is_not_followed(mirror):
    if not (mirror / "Rack_em_up" / "link.txt").is_symlink():
        pytest.skip("symlinks unavailable")
    assert X(action="read", repo="Rack_em_up", path="link.txt")["ok"] is False
    g = X(action="grep", repo="Rack_em_up", query="outside secret")
    assert g["ok"] is False


def test_blocked_files(mirror):
    for path in (".env", "node_modules/x/index.js", "flagged.ts", ".git/config"):
        r = X(action="read", repo="Rack_em_up", path=path)
        assert r["ok"] is False and FAKE_TOKEN not in json.dumps(r)
    assert X(action="read", repo="agent-tools", path="agent_tools/engine/.env")["ok"] is False
    assert X(action="read", repo="Rack_em_up", path=".env.example")["ok"] is True
    top = X(action="list", repo="Rack_em_up")
    assert ".env" not in top["entries"] and "node_modules/" not in top["entries"] and "flagged.ts" not in top["entries"]
    assert ".env.example" in top["entries"] and "src/" in top["entries"]
    g = X(action="grep", query="glicko")
    assert all("node_modules" not in h["path"] for h in g["hits"])


def test_redaction(mirror):
    r = X(action="read", repo="Rack_em_up", path="src/config.ts")
    s = json.dumps(r)
    assert r["ok"] and FAKE_TOKEN not in s and "abcd1234efgh5678" not in s and "<redacted:" in s and r["redacted"] >= 2
    g = X(action="grep", repo="Rack_em_up", query="token")
    assert FAKE_TOKEN not in json.dumps(g)
    assert R.find_secret_types("k = '" + FAKE_TOKEN + "'") == ["assigned_secret", "github_token"] or "github_token" in R.find_secret_types(FAKE_TOKEN)


def test_caps(mirror):
    r = X(action="read", repo="Rack_em_up", path="big.md", start_line=1, end_line=500)
    assert r["ok"] and len(r["lines"]) <= R.READ_LINES
    assert len(json.dumps(r, ensure_ascii=False, separators=(",", ":"))) <= R.OUT_LIMIT
    assert all(len(ln) <= R.LINE_CHARS + 8 for ln in r["lines"])
    g = X(action="grep", query="line")
    assert g["ok"] and len(g["hits"]) <= R.GREP_HITS and g["truncated"]
    assert len(H.tool_json(g, name="repo_search")) <= R.OUT_LIMIT
    assert len(H.tool_json({"x": "y" * 5000})) <= 1400  # other tools keep the old cap


def test_grep_read_list_grounded_and_deterministic(mirror):
    g = X(action="grep", repo="RealAi", query="def tool_subset")
    assert g["ok"] and g["hits"][0]["path"] == "realai/training/adapters_tools.py" and g["hits"][0]["line"] == 3
    assert X(action="grep", repo="RealAi", query="def tool_subset") == g
    blob = json.dumps(g)
    assert str(mirror) not in blob and ":\\\\" not in blob
    facts = H.key_facts("repo_search", g, {})
    assert "adapters_tools.py" in facts[0]
    rd = X(action="read", repo="Rack_em_up", path="README.md")
    assert rd["lines"][0] == "1: # RackUp" and rd["commit"] == "abc123def456"
    nm = X(action="grep", repo="RealAi", query="zzz-not-there")
    assert nm["ok"] is False and nm["error"] == "no matches"


def test_no_writes(mirror):
    def snap():
        return sorted((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in mirror.rglob("*") if not p.is_symlink())
    before = snap()
    for a in ({"action": "list"}, {"action": "grep", "query": "glicko"}, {"action": "read", "repo": "Rack_em_up", "path": "README.md"},
              {"action": "list", "repo": "Rack_em_up", "path": "src"}):
        H.execute("repo_search", a)
    assert snap() == before


def test_verifier_recomputes_repo_search(mirror):
    from realai.training.self_data.verify import verify

    args = {"action": "grep", "repo": "RealAi", "query": "def tool_subset"}
    res = H.execute("repo_search", args)
    msgs = [{"role": "user", "content": "Where is tool_subset defined in RealAi?"},
            {"role": "assistant", "content": "`tool_subset` is defined in realai/training/adapters_tools.py (line 3)."}]
    ok, why = verify(msgs, [{"name": "repo_search", "arguments": args, "result": res}])
    assert ok, why
    msgs[-1]["content"] = "It lives in some helper file."
    ok, why = verify(msgs, [{"name": "repo_search", "arguments": args, "result": res}])
    assert not ok and "repo_search_fact_missing" in why


def test_repos_spotcheck_suite_separate(mirror):
    from realai.training import spotcheck as S

    rep = S.checks_repos()
    ids = {c["id"] for c in rep}
    assert 9 <= len(rep) <= 12 and not ids & {c["id"] for c in S.checks()} and not ids & {c["id"] for c in S.checks_extended()}
    assert "repos" in S.SUITES and len(S.SUITES["all"]()) == len(S.checks()) + len(S.checks_extended())
    by = {c["id"]: c for c in rep}
    assert by["repo_grep_def"]["ok"]("It's in realai/training/adapters_tools.py.")
    assert not by["repo_grep_def"]["ok"]("It's in utils.py.")
    assert by["repo_secret_block"]["ok"]("I can't show that: .env files are blocked.")
    assert not by["repo_secret_block"]["ok"]("Sure:\nAPI_KEY = abcdefghij")
    r = S.run(lambda m, t: {"content": "no"}, only=["repos_available"], log=lambda m: None, suite="repos")
    assert r["suite"] == "repos" and r["n"] == 1


def test_repos_suite_without_mirror_expects_admission(monkeypatch, tmp_path):
    from realai.training import spotcheck as S

    monkeypatch.setenv("REALAI_REPO_MIRROR", str(tmp_path / "none"))
    by = {c["id"]: c for c in S.checks_repos()}
    assert by["repos_available"]["ok"]("The repo mirror isn't available yet.")
    assert not by["repos_available"]["ok"]("RealAi and Rack_em_up.")


def test_eval_prompts_include_repos_suite():
    from realai.training.dataset_builder.dedupe import normalize
    from realai.training.dataset_builder.pipeline import eval_prompts

    assert normalize("Which of my GitHub repos can you search locally?") in eval_prompts()
