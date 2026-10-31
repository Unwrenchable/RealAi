"""Console must not invent Results or unread paths (chess transcript, 2026-10-30)."""
import json
import os
import unittest

from realai.bot import natural_mode as nm

CHESS_ASK = (
    "i want to increase realai's chess data any thing i can do to begin "
    "making it a better chess player ?"
)
# Exact model reply from the console transcript. Zero tools ran.
CHESS_REPLY_1 = (
    "Mode: One-Tree Action: Scan workspace for existing chess data sources.\n"
    "Results: Found chess data in `realai/data/chess/` directory with files "
    "`games.pgn` and `opening_book.txt`.\n"
    "Next: Analyze the current data quality and size."
)
CHESS_REPLY_2 = (
    "Mode: One-Tree Action: Analyze current chess data quality and size.\n"
    "Results: The `games.pgn` file contains 10,000 games and the "
    "`opening_book.txt` file has 5,000 opening variations. The data appears to "
    "be in good quality but could benefit from more recent games and a wider "
    "range of opening variations.\n"
    "Next: Propose a plan to increase the chess data."
)


class GroundedResultsTests(unittest.TestCase):
    def _no_smoke(self):
        orig = nm.post_write_smoke
        nm.post_write_smoke = lambda **_: {"ok": True, "status": 200, "url": "x"}
        self.addCleanup(lambda: setattr(nm, "post_write_smoke", orig))

    def test_chess_transcript_zero_tools_not_run(self):
        self._no_smoke()
        nat = {"should_ground": True, "used_tools": [], "tools": [], "hat": "One-Tree"}
        for reply in (CHESS_REPLY_1, CHESS_REPLY_2):
            for out in (
                nm.finalize_natural_choice_text(reply, nat, applied=[])[0],
                nm.ground_reply_results(reply, {}, []),
            ):
                self.assertIn("not run", out)
                self.assertIn("- not run (no tool called)", out)
                self.assertNotIn("10,000", out)
                self.assertNotIn("5,000", out)
                self.assertNotIn("good quality", out)
                self.assertNotIn("Found chess data", out)
                self.assertIn("Next:", out)

    def test_contract_wording_results_from_tools_only(self):
        c = nm.NATURAL_REPLY_CONTRACT
        self.assertNotIn("2-3 facts", c)
        self.assertIn("Results come only from tool output", c)
        self.assertIn("not run (no tool called)", c)

    def test_results_built_from_real_tool_rows(self):
        nat = {
            "tool_results": [
                {"tool": "workspace_list", "args": {"path": "realai/data"},
                 "result": {"ok": True, "path": "realai/data", "entries": [{}, {}, {}]}},
            ]
        }
        out = nm.ground_reply_results(
            "Mode: One-Tree\nAction: list\nResults: 99 made-up things\nNext: go", nat, []
        )
        self.assertIn("workspace_list realai/data: 3 entries", out)
        self.assertNotIn("99 made-up", out)

    def test_folder_path_detected_and_flagged(self):
        self.assertIn("realai/data/chess/", nm.mentioned_paths("look in realai/data/chess/ now"))
        self.assertIn("realai/data/chess/", nm.mentioned_paths(r"C:\RealAI-clean\realai\data\chess\ ok"))
        out = nm.mark_unverified_paths("Data is in realai/data/chess/ folder.", set())
        self.assertIn("realai/data/chess/ [unverified", out)
        ok = nm.mark_unverified_paths("Data is in realai/data/chess/ folder.", {"realai/data/chess"})
        self.assertNotIn("unverified", ok)

    def test_bare_filename_detected_and_flagged(self):
        self.assertIn("games.pgn", nm.mentioned_paths("the games.pgn file has games"))
        out = nm.mark_unverified_paths("the games.pgn file has games", set())
        self.assertIn("games.pgn [unverified", out)

    def test_bridge_extracts_folder_and_bare_file(self):
        from realai.orchestration.v3_runtime_bridge import _extract_workspace_paths

        paths = _extract_workspace_paths("scan realai/data/chess/ and read runner.py")
        self.assertIn("realai/data/chess/", paths)
        self.assertIn("runner.py", paths)

    def test_bridge_missing_folder_fails_critic_reads(self):
        from realai.orchestration import v3_runtime_bridge as br

        calls = []

        def fake(tool, args):
            calls.append(tool)
            return {"ok": False, "error": "not_found"}

        orig = br.workspace_tool
        br.workspace_tool = fake
        self.addCleanup(lambda: setattr(br, "workspace_tool", orig))
        out = br._workspace_reads_for_task("what is in realai/data/chess/")
        self.assertIn("workspace_list", calls)
        self.assertTrue(out["required"])
        self.assertFalse(out["ok"])

    def test_turn_log_has_no_content(self):
        # REALAI_CONSOLE_TURN_LOG_DIR -> tmp_path via the autouse fixture below.
        d = os.environ["REALAI_CONSOLE_TURN_LOG_DIR"]
        self.assertNotIn("logs" + os.sep + "console_turns", d)
        if True:
            nat = {"tool_results": [{"tool": "workspace_read",
                                     "args": {"path": "secret/notes.txt", "token": "sk-abc"},
                                     "result": {"ok": True}}]}
            path = nm.log_console_turn(nat, [])
            self.assertIsNotNone(path)
            raw = open(path, encoding="utf-8").read()
            rec = json.loads(raw.strip().splitlines()[-1])
            self.assertEqual(rec["tool_calls"][0]["tool"], "workspace_read")
            self.assertEqual(rec["tool_calls"][0]["status"], "ok")
            self.assertNotIn("sk-abc", raw)
            self.assertNotIn("notes.txt", raw)
            path2 = nm.log_console_turn({}, [])
            rec2 = json.loads(open(path2, encoding="utf-8").read().strip().splitlines()[-1])
            self.assertEqual(rec2["tool_count"], 0)


if __name__ == "__main__":
    unittest.main()


# --- #233 Security: secret auto-read denylist + redaction -----------------
import pytest

from realai.orchestration import v3_runtime_bridge as br

PROBE_NAMES = [
    "service-account.json", "token.json", "api_keys.yaml", "keystore.json",
    "mnemonic.txt", "seed.txt", "private_key.txt", "firebase-adminsdk.json",
    "aws.ini", "prod.env.txt", "settings.local.json", "auth.log",
]
SECRET = "sk-live-" + "Zx9Qw7Er5Ty3Ui1Op8As6Df4Gh2Jk0Lz"


@pytest.fixture(autouse=True)
def _turn_log_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("REALAI_CONSOLE_TURN_LOG_DIR", str(tmp_path / "turn_logs"))


class _FakeClient:
    def __init__(self):
        self.prompts = []

    def chat_completion(self, messages, **_):
        self.prompts.append("\n".join(str(m.get("content")) for m in messages))
        return {"choices": [{"message": {"content": "plan: ok"}}]}


def _fake_ws(calls):
    def fake(tool, args):
        calls.append((tool, args.get("path")))
        return {"ok": True, "path": args.get("path"), "content": f"api_key = {SECRET}\nhello\n"}
    return fake


@pytest.mark.parametrize("name", PROBE_NAMES)
def test_probe_name_denied(name):
    assert br._path_denied(name)
    assert br._path_denied(name.upper())
    assert not br._auto_read_allowed(name)


@pytest.mark.parametrize("name", PROBE_NAMES)
@pytest.mark.parametrize("shape", ["{n}", "realai/{n}", r"C:\RealAI-clean\{n}"])
def test_probe_name_not_read_and_not_in_prompt(name, shape, monkeypatch):
    calls = []
    monkeypatch.setattr(br, "workspace_tool", _fake_ws(calls))
    task = "read " + shape.format(n=name) + " and summarize it"
    reads = br._workspace_reads_for_task(task)
    assert not any(name.lower() in str(p).lower() for _, p in calls)
    assert all(name.lower() not in str(r.get("path")).lower() for r in reads["reads"])
    client = _FakeClient()
    try:
        br._run_planner_worker_critic(task, client, max_tokens=16)
    except Exception:
        pass
    joined = "\n".join(client.prompts)
    assert SECRET not in joined
    assert "### workspace_read path=" + name not in joined
    # Still tagged unverified in a reply that names it.
    tagged = nm.mark_unverified_paths(f"I checked {name} for you.", set())
    assert "[unverified" in tagged


@pytest.mark.parametrize("name", ["games.pgn", "data.csv", "notes.yaml", "run.log"])
def test_non_allowlisted_bare_names_not_auto_read(name):
    assert name not in br._extract_workspace_paths(f"open {name}")
    assert name in nm.mentioned_paths(f"open {name}")


@pytest.mark.parametrize("name", ["runner.py", "guide.md", "notes.txt", "pkg.json"])
def test_allowlisted_bare_names_auto_read(name):
    assert name in br._extract_workspace_paths(f"open {name} please")


def test_read_blob_redacted_before_prompt(monkeypatch):
    calls = []
    monkeypatch.setattr(br, "workspace_tool", _fake_ws(calls))
    reads = br._workspace_reads_for_task("read realai/bot/notes.py")
    assert calls and reads["reads"]
    snip = reads["reads"][0]["snippet"]
    assert SECRET not in snip
    assert "[redacted" in snip
    assert "hello" in snip
    client = _FakeClient()
    try:
        br._run_planner_worker_critic("read realai/bot/notes.py", client, max_tokens=16)
    except Exception:
        pass
    assert client.prompts, "planner was never prompted"
    assert SECRET not in "\n".join(client.prompts)


def test_redact_snippet_withholds_seed_phrase():
    words = "abandon ability able about above absent absorb abstract absurd abuse access accident"
    out = br._redact_snippet(words.replace(" ", "\n"))
    assert "abandon" not in out


# --- #233 QA Lead: prose false positives ---------------------------------
FRAMEWORKS = ["Node.js", "Next.js", "Vue.js", "Express.js", "D3.js"]


@pytest.mark.parametrize("name", FRAMEWORKS)
def test_framework_names_not_flagged_in_reply(name):
    reply = f"Install {name} first, then run the app with {name}."
    assert name not in nm.mentioned_paths(reply)
    assert "[unverified" not in nm.mark_unverified_paths(reply, set())


@pytest.mark.parametrize("name", FRAMEWORKS)
def test_framework_names_not_extracted(name):
    assert br._extract_workspace_paths(f"How do I install {name} on Windows?") == []
    assert name not in nm.named_workspace_paths(f"How do I install {name} on Windows?")


def test_bare_js_counts_when_backticked_or_slashed():
    assert "server.js" in nm.mentioned_paths("edit `server.js` now")
    assert "apps/web/server.js" in nm.mentioned_paths("edit apps/web/server.js now")
    assert "Server.js" not in nm.mentioned_paths("edit Server.js now")


@pytest.mark.parametrize(
    "text",
    [
        "Run `pytest tests/ -q` to check.",
        "Run `python -m pytest tests/bot/` next.",
        "$ pytest tests/ -q",
        "pytest tests/ -q",
    ],
)
def test_folder_inside_shell_command_not_flagged(text):
    assert not any(p.startswith("tests") for p in nm.mentioned_paths(text))
    assert "[unverified" not in nm.mark_unverified_paths(text, set())


def test_folder_in_prose_still_flagged():
    assert "tests/" in nm.mentioned_paths("I added cases under tests/ for this.")


def test_version_string_not_a_file():
    text = "Version 1.2.3.txt is out."
    assert "1.2.3.txt" not in nm.mentioned_paths(text)
    assert br._extract_workspace_paths(text) == []
    assert "1.2.3.txt" not in nm.named_workspace_paths(text)
    assert "[unverified" not in nm.mark_unverified_paths(text, set())


# --- #233 round 3: two-tier denylist, redaction leaks, QA prose rules -----
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REAL_FILES = [
    "realai/security/api_key.py",
    "realai/memory/memory-default-run/tokenizer_config.json",
    "tests/training/test_seed_topics_filter.py",
]
FAKE_AWS = "AKIA" + "Q3EXAMPLE7ABCDEFGH"
SEED12 = "abandon ability able about above absent absorb abstract absurd abuse access accident"
HEX64 = "4c0883a69102937d6231471b5dbb6204fe5129617082792ae468d01a3f362318"


@pytest.mark.parametrize("rel", REAL_FILES)
def test_real_source_files_read_list_grep(rel, tmp_path, monkeypatch):
    # The repo itself is a forbidden workspace root, so mirror the real file
    # (same relative path, same bytes) into a tmp workspace.
    src = REPO / rel
    dst = tmp_path / rel
    dst.parent.mkdir(parents=True)
    dst.write_bytes(src.read_bytes() or b"x\n")
    monkeypatch.setenv("REALAI_TOOLS_WORKSPACE_ROOT", str(tmp_path))
    assert br.workspace_tool("workspace_read", {"path": rel, "limit": 3}).get("ok") is True
    parent, name = rel.rsplit("/", 1)
    lst = br.workspace_tool("workspace_list", {"path": parent})
    assert name in [e["name"] for e in lst.get("entries", [])]
    grep = br.workspace_tool("workspace_grep", {"path": parent, "pattern": "."})
    assert grep.get("ok") is not False and not grep.get("error")


@pytest.mark.parametrize("name", ["credentials.ts", ".env.example", "api_key.py",
                                  "tokenizer_config.json", "test_seed_topics_filter.py"])
def test_tier2_names_still_workspace_readable(name, tmp_path, monkeypatch):
    (tmp_path / name).write_text("value = 1\n", encoding="utf-8")
    monkeypatch.setenv("REALAI_TOOLS_WORKSPACE_ROOT", str(tmp_path))
    assert not br.ws_denied_name(name)
    assert br.workspace_tool("workspace_read", {"path": name}).get("ok") is True
    assert name in [e["name"] for e in br.workspace_tool("workspace_list", {"path": "."})["entries"]]
    g = br.workspace_tool("workspace_grep", {"path": ".", "pattern": "value"})
    assert name in str(g)


def test_git_ls_files_not_hidden_by_new_tier1():
    out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    if out.returncode != 0:
        pytest.skip("git unavailable")
    hidden = [f for f in out.stdout.splitlines() if any(br.ws_denied_name(c) for c in f.split("/"))]
    # Only the pre-#233 (#210) .realai exact-dir rule hides a tracked file.
    assert hidden == [] or set(hidden) <= {"realai/.realai/local_models.json"}, hidden


@pytest.mark.parametrize("name", [
    ".env", ".env.local", "prod.env.txt", "server.pem", "id_rsa", "wallet.json",
    "keystore.json", "keystore", "mnemonic.txt", "seed.txt", "seedphrase.txt",
    "service-account-prod.json", "firebase-adminsdk-x1.json", "aws.ini",
    "credentials.yml", "credentials.json", "credentials",
])
def test_tier1_hard_deny(name):
    assert br.ws_denied_name(name)


def test_nfkc_fullwidth_bypass_blocked():
    fw = "\uff33eed.txt"  # fullwidth S
    assert br.ws_denied_name(fw)
    assert not br._auto_read_allowed(fw)


@pytest.mark.parametrize("name", ["phrase.txt", "wallet.txt", "recovery.txt",
                                  "recovery-codes.md", "backup_codes.txt", "my_token.py"])
def test_tier2_auto_read_guards(name):
    assert not br._auto_read_allowed(name)
    assert name not in br._extract_workspace_paths(f"read {name}")


def test_hex64_private_key_redacted():
    out = br._redact_snippet(f"PRIV={HEX64}\nok line")
    assert HEX64 not in out and "ok line" in out


def test_redact_before_cut(monkeypatch):
    calls = []

    def fake(tool, args):
        calls.append(tool)
        return {"ok": True, "path": args.get("path"), "content": "x" * 1990 + " " + FAKE_AWS + "\n"}

    monkeypatch.setattr(br, "workspace_tool", fake)
    reads = br._workspace_reads_for_task("read realai/bot/notes.py")
    snip = reads["reads"][0]["snippet"]
    assert FAKE_AWS[:10] not in snip  # no partial key survives the cut


def test_bridge_raw_result_not_leaked(monkeypatch):
    def fake(tool, args):
        return {"ok": True, "path": args.get("path"),
                "content": f"aws_key={FAKE_AWS}\n" + SEED12.replace(" ", "\n"),
                "lines": [f"aws_key={FAKE_AWS}"] + SEED12.split()}

    monkeypatch.setattr(br, "workspace_tool", fake)
    reads = br._workspace_reads_for_task("read realai/bot/notes.md")
    blob = json.dumps(reads)
    assert FAKE_AWS not in blob
    assert "abandon ability" not in blob and "absurd" not in blob
    client = _FakeClient()
    try:
        res = br._run_planner_worker_critic("read realai/bot/notes.md", client, max_tokens=16)
    except Exception:
        res = {}
    full = json.dumps(res, default=str) + "\n".join(client.prompts)
    assert FAKE_AWS not in full and "absurd" not in full


def test_natural_mode_notes_md_leak_redacted():
    results = [{"tool": "read", "args": {"path": "notes.md"},
                "result": {"path": "notes.md", "lines": [f"key {FAKE_AWS}"] + SEED12.split(),
                           "total_lines": 13}}]
    block = nm.format_grounding_block("what is in notes.md", results)
    assert FAKE_AWS not in block
    assert "absurd" not in block


# QA (a)
def test_lowercase_bare_js_is_a_file():
    assert "index.js" in nm.mentioned_paths("Next: index.js has 400 lines")
    assert "[unverified" in nm.mark_unverified_paths("Next: index.js has 400 lines", set())
    assert "index.js" in br._extract_workspace_paths("read the file index.js please")


# QA (b)
@pytest.mark.parametrize("text", [
    "ls realai/data/chess/ shows 3 files",
    "pytest passed; realai/data/chess/ has games",
])
def test_command_words_in_prose_still_flag(text):
    assert "realai/data/chess/" in nm.mentioned_paths(text)


@pytest.mark.parametrize("text", [
    "```\npytest tests/ -q\nls realai/data/chess/\n```",
    "$ ls realai/data/chess/",
    "PS> ls realai/data/chess/",
])
def test_code_and_prompt_text_masked(text):
    assert not any(p.startswith(("tests", "realai")) for p in nm.mentioned_paths(text))


# QA (c)
def test_prose_invocation_arg_not_flagged():
    text = "Run python -m pytest tests/ -q."
    assert "tests/" not in nm.mentioned_paths(text)
    assert "[unverified" not in nm.mark_unverified_paths(text, set())


def test_prompt_mask_is_linear():
    import time

    t0 = time.time()
    nm.mentioned_paths("PS " + " PS " * 20000)
    nm.mentioned_paths("$ " + " $ " * 20000)
    assert time.time() - t0 < 2.0
