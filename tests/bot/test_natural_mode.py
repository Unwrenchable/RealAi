"""Natural Mode: plain-English Console chat is tools-first, not a slash manual."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from realai.bot.boot import HARD_IDENTITY_LOCK
from realai.bot.natural_mode import (
    NATURAL_GROUNDING_RULE,
    apply_natural_grounding,
    extract_path_tokens,
    is_explicit_command,
    looks_like_repo_ask,
    plan_natural_inspect,
)
from realai.cli.craft import _should_auto_inspect
from realai.meta_router import classify_task, route_task


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
