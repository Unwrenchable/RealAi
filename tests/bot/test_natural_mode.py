"""Natural Mode: plain-English Console chat is tools-first, not a slash manual."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from realai.bot.boot import HARD_IDENTITY_LOCK, chat_system_prefix
from realai.bot.natural_mode import (
    NATURAL_GROUNDING_RULE,
    apply_natural_grounding,
    apply_workspace_intent,
    extract_learn_source,
    extract_path_tokens,
    extract_write_spec,
    is_explicit_command,
    looks_like_agent_ask,
    looks_like_learn_ask,
    looks_like_repo_ask,
    looks_like_write_ask,
    match_ability_ids,
    plan_natural_auto,
    plan_natural_inspect,
    plan_natural_write,
    should_natural_act,
)
from realai.bot.workspace_intent import (
    clear_session_workspace,
    extract_workspace_target,
    looks_like_workspace_switch,
)
from realai.cli.craft import _should_auto_inspect
from realai.meta_router import classify_task, route_task
from realai.workspace import get_request_workspace, set_request_workspace


class TestNaturalDetector(unittest.TestCase):
    def test_slash_is_explicit(self):
        self.assertTrue(is_explicit_command("/heal"))
        self.assertTrue(is_explicit_command("/multi hive next"))
        self.assertTrue(is_explicit_command("$ whoami"))
        self.assertFalse(is_explicit_command("what's in console.html"))

    def test_empty_state_asks_are_repo(self):
        self.assertTrue(looks_like_repo_ask("what's in this repo"))
        self.assertTrue(looks_like_repo_ask("read console.html"))
        self.assertTrue(looks_like_repo_ask("list the workspace files"))
        self.assertTrue(looks_like_repo_ask("fix the hive health check"))
        self.assertTrue(looks_like_repo_ask("find where console.html is served"))

    def test_smalltalk_is_not_repo(self):
        self.assertFalse(looks_like_repo_ask("hello there"))
        self.assertFalse(looks_like_repo_ask("hey, what can you help me with?"))
        self.assertFalse(looks_like_repo_ask("/tools"))
        self.assertFalse(should_natural_act("hello there"))
        self.assertFalse(should_natural_act("/multi hive next"))

    def test_create_file_is_write_not_inspect_only(self):
        ask = "create file docs/recovery/_auditor_probe.txt with content PROBE_OK"
        self.assertTrue(looks_like_write_ask(ask))
        self.assertTrue(should_natural_act(ask))
        path, content = extract_write_spec(ask)
        self.assertEqual(path, "docs/recovery/_auditor_probe.txt")
        self.assertEqual(content, "PROBE_OK")
        self.assertEqual(plan_natural_write("what's in hello.txt"), [])

    def test_natural_write_skips_protected_core_modules(self):
        ask = "create file realai/bot/live_exec.py with content MISSION_SCRAP"
        path, content = extract_write_spec(ask)
        self.assertEqual(path, "realai/bot/live_exec.py")
        self.assertEqual(content, "MISSION_SCRAP")
        self.assertEqual(plan_natural_write(ask), [])
        orch = "create file realai/orchestration/v3_orchestrator.py with content NOPE"
        self.assertEqual(plan_natural_write(orch), [])


class TestNaturalAutoPlan(unittest.TestCase):
    def test_learn_ask_detects_windows_and_url(self):
        self.assertTrue(looks_like_learn_ask("learn from this folder"))
        self.assertTrue(looks_like_learn_ask("learn from C:\\path\\to\\folder"))
        self.assertTrue(looks_like_learn_ask("git-learn https://github.com/acme/app"))
        self.assertFalse(looks_like_learn_ask("what's in this repo"))
        self.assertFalse(looks_like_learn_ask("/learn C:\\path\\to\\folder"))

    def test_extract_learn_source_windows_and_quoted(self):
        self.assertEqual(
            extract_learn_source(r"learn from C:\path\to\folder"),
            r"C:\path\to\folder",
        )
        self.assertEqual(
            extract_learn_source(r'learn from "C:\path with spaces\repo"'),
            r"C:\path with spaces\repo",
        )
        self.assertEqual(extract_learn_source("learn from this folder"), ".")
        self.assertEqual(
            extract_learn_source("learn from https://github.com/acme/app.git"),
            "https://github.com/acme/app.git",
        )

    def test_audit_and_broken_plan_without_slash(self):
        self.assertTrue(looks_like_agent_ask("audit this repo"))
        self.assertTrue(should_natural_act("audit this repo"))
        self.assertTrue(should_natural_act("what's broken"))
        kinds = [k for k, _ in plan_natural_auto("audit this repo")]
        self.assertIn("agents", kinds)
        kinds_b = [k for k, _ in plan_natural_auto("what's broken")]
        self.assertIn("doctor", kinds_b)
        file_kinds = [k for k, _ in plan_natural_auto("read console.html")]
        self.assertEqual(file_kinds, [])

    def test_ability_phrases_match_catalog(self):
        ids = match_ability_ids("give me a rackup coach practice plan")
        self.assertIn("coach", ids)
        ids2 = match_ability_ids("run text to speech on this line")
        self.assertIn("audio_speech", ids2)
        self.assertFalse(match_ability_ids("hello there"))

    def test_learn_plan_skips_slash(self):
        plans = plan_natural_auto("learn from ./my-repo")
        self.assertTrue(any(k == "learn" for k, _ in plans), plans)
        src = [a.get("source") for k, a in plans if k == "learn"][0]
        self.assertEqual(src, "./my-repo")

    def test_extract_console_html(self):
        self.assertIn("console.html", extract_path_tokens("what's in console.html"))
        self.assertIn("apps/vscode/webview/console.html", extract_path_tokens("read apps/vscode/webview/console.html"))


class TestRoutingPrefersCoder(unittest.TestCase):
    def test_file_ask_classifies_code(self):
        self.assertEqual(classify_task("what's in console.html"), "code")
        self.assertEqual(classify_task("fix the login bug"), "code")

    def test_file_ask_routes_coder_in_product(self):
        d = route_task("what's in console.html", mode="product")
        self.assertEqual(d.target, "coder")
        self.assertEqual(d.task_class, "code")

    def test_product_smalltalk_stays_overseer(self):
        d = route_task("hello there", mode="product")
        self.assertEqual(d.target, "overseer")


class TestCraftInspectProductTree(unittest.TestCase):
    def test_product_file_ask_auto_inspects(self):
        self.assertTrue(_should_auto_inspect("what's in console.html"))
        self.assertFalse(_should_auto_inspect("hello there"))
        self.assertFalse(_should_auto_inspect("/heal"))

    def test_plan_includes_read_for_named_file(self):
        plans = plan_natural_inspect("what's in console.html")
        names = [n for n, _ in plans]
        self.assertIn("read", names)
        reads = [kw.get("path") for n, kw in plans if n == "read"]
        self.assertTrue(any(str(p).replace("\\", "/").endswith("console.html") for p in reads), reads)


class TestChatSystemPrefix(unittest.TestCase):
    def test_prefix_includes_lock_and_operator(self):
        text = chat_system_prefix(
            "When the user asks about files or code: read/list/grep first — never invent contents."
        )
        self.assertIn("Never invent file contents", text)
        self.assertIn("never invent contents", text.lower())


class TestWorkspaceIntent(unittest.TestCase):
    def test_extract_work_in_windows_path(self):
        self.assertTrue(looks_like_workspace_switch(r"work in C:\Users\tsmit\Rack_em_up"))
        self.assertEqual(
            extract_workspace_target(r"work in C:\Users\tsmit\Rack_em_up"),
            r"C:\Users\tsmit\Rack_em_up",
        )

    def test_switch_local_folder_and_verify_write(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        sid = "test-ws-intent"
        self.addCleanup(lambda: clear_session_workspace(sid))
        self.addCleanup(lambda: set_request_workspace(None))
        prev = {
            k: os.environ.get(k)
            for k in (
                "REALAI_WORKSPACE",
                "REALAI_HOME",
                "REALAI_PRODUCT_ROOT",
                "REALAI_ROOT",
                "REALAI_EXTRA_WRITE_ROOTS",
                "REALAI_EXTRA_READ_ROOTS",
                "REALAI_EXTRA_WORKSPACES",
            )
        }

        def _restore_env():
            for k, v in prev.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

        self.addCleanup(_restore_env)
        os.environ.pop("REALAI_EXTRA_WRITE_ROOTS", None)
        os.environ.pop("REALAI_EXTRA_READ_ROOTS", None)
        os.environ.pop("REALAI_EXTRA_WORKSPACES", None)

        switched = apply_workspace_intent(f"work in {root}", session_id=sid)
        self.assertTrue(switched.get("switched"), switched)
        self.assertEqual(Path(switched["workspace"]), root.resolve())
        self.assertEqual(get_request_workspace(), root.resolve())

        note = root / "note.txt"
        body = {"session_id": sid}
        ask = "create file note.txt with content HELLO_WS"
        ground = apply_natural_grounding(body, ask)
        self.assertTrue(ground.get("wrote"), ground)
        self.assertTrue(ground.get("short_circuit"), ground)
        self.assertTrue(note.is_file())
        self.assertEqual(note.read_text(encoding="utf-8"), "HELLO_WS")
        self.assertIn("verify=ok", str(ground.get("reply") or ""))
        self.assertIn("HELLO_WS", str(ground.get("reply") or ""))


class TestGroundingLock(unittest.TestCase):
    def test_identity_lock_forbids_invented_files(self):
        self.assertIn("Never invent file contents", HARD_IDENTITY_LOCK)
        self.assertIn("GROUNDING LOCK", NATURAL_GROUNDING_RULE)

    def test_apply_grounding_splices_tool_results(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "hello.txt").write_text("alpha-ground-token\n", encoding="utf-8")
        env_keys = ("REALAI_WORKSPACE", "REALAI_HOME", "REALAI_PRODUCT_ROOT", "REALAI_ROOT")
        prev = {k: os.environ.get(k) for k in env_keys}
        cwd = os.getcwd()
        try:
            os.environ["REALAI_WORKSPACE"] = str(root)
            os.chdir(root)
            body = {"messages": [{"role": "user", "content": "what's in hello.txt"}]}
            meta = apply_natural_grounding(body, "what's in hello.txt")
            self.assertTrue(meta.get("should_ground"))
            content = str((body["messages"][-1] or {}).get("content") or "")
            if meta.get("admit_failure"):
                self.assertIn("won't invent", meta.get("failure_text") or "")
            else:
                self.assertIn("alpha-ground-token", content)
                self.assertIn("Never invent", content)
        finally:
            os.chdir(cwd)
            for k, v in prev.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


if __name__ == "__main__":
    unittest.main()
