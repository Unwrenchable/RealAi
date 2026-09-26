"""Natural Mode: plain-English Console chat is tools-first, not a slash manual."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from realai.bot.boot import HARD_IDENTITY_LOCK, chat_system_prefix, load_operator_directive
from realai.bot.natural_mode import (
    NATURAL_GROUNDING_RULE,
    NATURAL_REPLY_CONTRACT,
    apply_natural_grounding,
    apply_workspace_intent,
    extract_learn_source,
    MAX_TOOLS_THIS_TURN,
    extract_path_tokens,
    extract_write_spec,
    is_explicit_command,
    looks_like_agent_ask,
    looks_like_learn_ask,
    looks_like_repo_ask,
    looks_like_write_ask,
    match_ability_ids,
    named_workspace_paths,
    plan_natural_auto,
    plan_natural_inspect,
    plan_natural_turn,
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
        self.assertEqual(names[0], "workspace_read")
        self.assertLessEqual(len(plans), MAX_TOOLS_THIS_TURN)
        reads = [kw.get("path") for n, kw in plans if n == "workspace_read"]
        self.assertIn("apps/vscode/webview/console.html", reads)


class TestNamedPathAutoRead(unittest.TestCase):
    """Named files are workspace_read first, inside the 3-tool cap.

    The bridge critic fails a turn that names a path and never reads it.
    These plans are the happy path for that rule.
    """

    def _reads(self, plans):
        return [kw.get("path") for name, kw in plans if name == "workspace_read"]

    def test_cap_stays_three(self):
        self.assertEqual(MAX_TOOLS_THIS_TURN, 3)

    def test_console_webview_and_windows_paths_match_critic(self):
        from realai.orchestration.v3_runtime_bridge import _extract_workspace_paths

        samples = [
            "what's in console.html",
            "quote apps/vscode/webview/console.html",
            r"propose a css change for C:\RealAI-clean\apps\vscode\webview\console.html",
            "read apps/vscode/webview/console.html",
        ]
        for ask in samples:
            critic = _extract_workspace_paths(ask)
            self.assertTrue(critic, ask)
            ours = named_workspace_paths(ask)
            for path in critic:
                self.assertIn(path, ours, ask)
            plans = plan_natural_turn(ask)
            self.assertTrue(plans, ask)
            self.assertEqual(plans[0][0], "workspace_read", plans)
            self.assertEqual(plans[0][1]["path"], critic[0], plans)
            self.assertLessEqual(len(plans), MAX_TOOLS_THIS_TURN, plans)
            self.assertEqual(plan_natural_write(ask), [])
            self.assertNotIn("write", [name for name, _ in plans])

    def test_readme_root_is_not_retargeted_unless_critic_says_so(self):
        self.assertEqual(named_workspace_paths("what's in README.md"), ["README.md"])
        self.assertEqual(
            named_workspace_paths("read README.md"),
            ["apps/vscode/README.md"],
        )
        plans = plan_natural_write("create file README.md with content HI")
        self.assertEqual(plans[0][1]["path"], "README.md")
        gold = plan_natural_write("create file console.html with content HI")
        self.assertEqual(gold[0][1]["path"], "apps/vscode/webview/console.html")

    def test_propose_reads_before_any_other_tool(self):
        ask = "propose a css change for console.html"
        self.assertFalse(looks_like_write_ask(ask))
        plans = plan_natural_turn(ask)
        self.assertEqual([name for name, _ in plans], ["workspace_read"])
        self.assertEqual(self._reads(plans), ["apps/vscode/webview/console.html"])

    def test_named_read_leaves_room_for_one_follow_on_tool(self):
        plans = plan_natural_turn("quote console.html and what's broken")
        kinds = [name for name, _ in plans]
        self.assertEqual(kinds[0], "workspace_read")
        self.assertIn("doctor", kinds)
        self.assertLessEqual(len(plans), MAX_TOOLS_THIS_TURN)

    def test_three_named_files_fill_the_cap(self):
        plans = plan_natural_turn("quote a.py b.ts c.md and what's broken")
        self.assertEqual(len(plans), MAX_TOOLS_THIS_TURN)
        self.assertTrue(all(name == "workspace_read" for name, _ in plans), plans)
        self.assertEqual(self._reads(plans), ["a.py", "b.ts", "c.md"])

    def test_audit_of_a_named_file_reads_first(self):
        plans = plan_natural_turn("audit console.html")
        kinds = [name for name, _ in plans]
        self.assertEqual(kinds[0], "workspace_read")
        self.assertIn("agents", kinds)
        self.assertLessEqual(len(plans), MAX_TOOLS_THIS_TURN)
        self.assertNotIn("pwd", kinds)

    def test_quote_executes_workspace_read(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        (root / "hello.txt").write_text("alpha-ground-token\n", encoding="utf-8")
        env_keys = ("REALAI_WORKSPACE", "REALAI_HOME", "REALAI_PRODUCT_ROOT", "REALAI_ROOT")
        prev = {k: os.environ.get(k) for k in env_keys}
        cwd = os.getcwd()

        def _restore():
            os.chdir(cwd)
            for k, v in prev.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

        self.addCleanup(_restore)
        os.environ["REALAI_WORKSPACE"] = str(root)
        os.chdir(root)
        ask = "quote hello.txt"
        body = {"messages": [{"role": "user", "content": ask}]}
        meta = apply_natural_grounding(body, ask)
        self.assertTrue(meta.get("should_ground"), meta)
        self.assertFalse(meta.get("wrote"), meta)
        self.assertFalse(meta.get("admit_failure"), meta)
        used = list(meta.get("used_tools") or [])
        self.assertEqual(used, ["workspace_read"])
        content = str((body["messages"][-1] or {}).get("content") or "")
        self.assertIn("alpha-ground-token", content)
        self.assertIn("Never say LANDED", content)

    def test_write_still_lands_only_after_write_and_counts_the_read(self):
        root = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(root, ignore_errors=True))
        env_keys = ("REALAI_WORKSPACE", "REALAI_HOME", "REALAI_PRODUCT_ROOT", "REALAI_ROOT")
        prev = {k: os.environ.get(k) for k in env_keys}
        cwd = os.getcwd()

        def _restore():
            os.chdir(cwd)
            for k, v in prev.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

        self.addCleanup(_restore)
        os.environ["REALAI_WORKSPACE"] = str(root)
        os.chdir(root)
        ask = "create file notes/desk.txt with content HELLO_WS"
        body = {"messages": [{"role": "user", "content": ask}]}
        meta = apply_natural_grounding(body, ask)
        self.assertTrue(meta.get("wrote"), meta)
        self.assertFalse(meta.get("admit_failure"), meta)
        used = list(meta.get("used_tools") or [])
        self.assertEqual(used[0], "workspace_read", used)
        self.assertIn("write", used)
        self.assertLessEqual(meta.get("tool_count"), MAX_TOOLS_THIS_TURN, meta)
        self.assertTrue((root / "notes" / "desk.txt").is_file())
        self.assertEqual((root / "notes" / "desk.txt").read_text(encoding="utf-8"), "HELLO_WS")
        reply = str(meta.get("reply") or "")
        self.assertNotIn("LANDED", reply.split("--- on disk", 1)[0])


class TestChatSystemPrefix(unittest.TestCase):
    def test_prefix_includes_lock_and_operator(self):
        text = chat_system_prefix(
            "When the user asks about files or code: read/list/grep first — never invent contents."
        )
        self.assertIn("Never invent file contents", text)
        self.assertIn("never invent contents", text.lower())
        self.assertIn("EXECUTE", text)
        self.assertIn("MAX_TOOLS_THIS_TURN=3", text)
        self.assertIn("180s", text)
        self.assertIn("LANDED", text)

    def test_directive_loads_without_env_file(self):
        prev_file = os.environ.pop("REALAI_OPERATOR_SYSTEM_FILE", None)
        prev_sys = os.environ.pop("REALAI_OPERATOR_SYSTEM", None)

        def _restore(key: str, val):
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val

        self.addCleanup(lambda: _restore("REALAI_OPERATOR_SYSTEM_FILE", prev_file))
        self.addCleanup(lambda: _restore("REALAI_OPERATOR_SYSTEM", prev_sys))
        text = load_operator_directive()
        self.assertIn("Reply contract", text)
        self.assertIn("MAX_TOOLS_THIS_TURN=3", text)
        self.assertIn("180s", text)
        self.assertIn("LANDED", text)
        self.assertIn("atomic_fizz_hive_client", text)
        prefix = chat_system_prefix("")
        self.assertIn(NATURAL_REPLY_CONTRACT.splitlines()[0], prefix)
        self.assertIn("Console Operator", prefix)


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
        reply = str(ground.get("reply") or "")
        self.assertIn("Mode:", reply)
        self.assertIn("Action:", reply)
        self.assertIn("Results:", reply)
        self.assertIn("Next:", reply)
        self.assertIn("HELLO_WS", reply)
        self.assertNotIn("LANDED", reply.split("--- on disk", 1)[0])


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


class TestPostWriteSmoke(unittest.TestCase):
    def test_hive_down_is_guarded_failure(self):
        from realai.bot.natural_mode import post_write_smoke

        prev = os.environ.get("REALAI_API_BASE")
        os.environ["REALAI_API_BASE"] = "http://127.0.0.1:9"
        try:
            out = post_write_smoke(timeout=0.4)
        finally:
            if prev is None:
                os.environ.pop("REALAI_API_BASE", None)
            else:
                os.environ["REALAI_API_BASE"] = prev
        self.assertFalse(out.get("ok"))
        self.assertTrue(out.get("post_step"))
        self.assertTrue(out.get("error") or out.get("guarded"))

    def test_smoke_fail_does_not_claim_success(self):
        from realai.bot import natural_mode as nm

        orig = nm.post_write_smoke
        nm.post_write_smoke = lambda **_k: {
            "ok": False,
            "url": "http://127.0.0.1:8001/health",
            "error": "connection refused",
            "post_step": True,
            "guarded": True,
        }
        self.addCleanup(lambda: setattr(nm, "post_write_smoke", orig))
        reply = nm.format_write_verified_reply(
            {"ok": True, "path": "notes/desk.txt", "bytes": 5},
            {"path": "notes/desk.txt", "content": "hello\n", "total_lines": 1},
            nm.post_write_smoke(),
        )
        self.assertIn("hive smoke failed", reply)
        self.assertIn("FAIL", reply)
        self.assertNotIn("smoke passed", reply)
        self.assertNotIn("LANDED", reply.split("--- on disk", 1)[0])
        shaped, smoke = nm.finalize_natural_choice_text(
            "LANDED the patch in app.py",
            {"should_ground": True, "used_tools": ["read"]},
            applied=[],
        )
        self.assertIn("Mode:", shaped)
        self.assertIn("PROPOSED", shaped)
        self.assertNotIn("LANDED", shaped)
        self.assertIsNone(smoke)

    def test_core_desk_tools_are_real(self):
        from realai.cli.craft import plan_tools, tool_git_diff, tool_git_status
        from realai.orchestration.v3_runtime_bridge import execute_registry_tool

        status = tool_git_status()
        self.assertTrue(status.get("branch") or status.get("error") or status.get("workspace"))
        diff = tool_git_diff()
        self.assertIn("ok", diff)
        plans = plan_tools("/git diff")
        self.assertEqual(plans[0][0], "git_diff")
        reg = execute_registry_tool("git_status", {})
        self.assertIn("tool", reg)
        learn = execute_registry_tool("learn_status", {})
        self.assertIn("count", learn)
        self.assertTrue(learn.get("ok") or learn.get("error"))


if __name__ == "__main__":
    unittest.main()
