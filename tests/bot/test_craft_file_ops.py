"""Craft file ops on the Console chat path: /write and natural create/fix."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from realai.bot.easy_tools import parse_easy_tool
from realai.bot.live_exec import wants_live_exec
from realai.bot.natural_mode import (
    apply_natural_grounding,
    extract_write_spec,
    looks_like_patch_ask,
    looks_like_write_ask,
    plan_natural_write,
)
from realai.cli.craft import apply_suggested_writes, is_protected_core_path, tool_write


class _WorkspaceTmp(unittest.TestCase):
    def setUp(self):
        self._cwd = os.getcwd()
        self._env = {
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
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "hello.txt").write_text("alpha-ground-token\n", encoding="utf-8")
        os.environ["REALAI_WORKSPACE"] = str(self.root)
        # Machine-wide EXTRA_WRITE=C:\ would defeat path sandbox assertions.
        os.environ.pop("REALAI_EXTRA_WRITE_ROOTS", None)
        os.environ.pop("REALAI_EXTRA_READ_ROOTS", None)
        os.environ.pop("REALAI_EXTRA_WORKSPACES", None)
        os.chdir(self.root)
        try:
            from realai.workspace import set_request_workspace

            set_request_workspace(None)
        except Exception:
            pass

    def tearDown(self):
        os.chdir(self._cwd)
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        try:
            from realai.workspace import set_request_workspace

            set_request_workspace(None)
        except Exception:
            pass
        self._tmp.cleanup()


class TestLiveExecDoesNotClaimCraftFileVerbs(unittest.TestCase):
    def test_write_read_list_grep_git_pwd_are_not_live_exec(self):
        for text in (
            "/write docs/recovery/_auditor_probe.txt PROBE_OK",
            "/write foo.py print('hi')",
            "/read console.html",
            "/list .",
            "/grep wants_live_exec",
            "/git",
            "/pwd",
            "/ls src",
            "/craft write docs/note.txt hello",
        ):
            self.assertFalse(wants_live_exec(text), text)

    def test_real_shell_asks_still_want_live_exec(self):
        self.assertTrue(wants_live_exec("$ whoami"))
        self.assertTrue(wants_live_exec("/run dir"))
        self.assertTrue(wants_live_exec("run `hostname`"))

    def test_long_policy_paste_is_not_live_exec(self):
        paste = (
            "Work like a desktop coding agent. LOOP every request: "
            "INSPECT read/list/grep real files. Never invent contents. "
            "ACT write with Craft. VERIFY re-read. REPORT short. "
            + ("x" * 200)
        )
        self.assertGreater(len(paste), 280)
        self.assertFalse(wants_live_exec(paste))
        self.assertFalse(wants_live_exec("type this and run that " + ("policy " * 40)))

    def test_prose_with_type_and_run_does_not_steal_turn(self):
        from realai.bot.live_exec import try_live_exec

        prose = "I type and run commands. Prefer tools. Never invent stdout."
        self.assertFalse(wants_live_exec(prose))
        self.assertIsNone(try_live_exec(prose))

        policy = (
            "Work like a desktop coding agent (same loop as our Grok Bot sessions), "
            "not a chatbot.\nLOOP — every request:\n"
            "1) INSPECT — read/list/grep real files.\n"
            "Prove it: read docs/CONSOLE_OPERATOR_DIRECTIVE.md"
        )
        self.assertFalse(wants_live_exec(policy))
        self.assertIsNone(try_live_exec(policy))

    def test_run_whoami_still_live_exec(self):
        from realai.bot.live_exec import try_live_exec

        self.assertTrue(wants_live_exec("run whoami"))
        dispatch = try_live_exec("run whoami")
        self.assertEqual((dispatch or {}).get("surface"), "live_exec")
        self.assertNotEqual(
            ((dispatch or {}).get("result") or {}).get("error"),
            "need_explicit_command",
        )


class TestEasyToolsDoesNotStealCraftFileVerbs(unittest.TestCase):
    def test_write_and_read_are_not_easy_tools(self):
        self.assertIsNone(parse_easy_tool("/write docs/note.txt hello"))
        self.assertIsNone(parse_easy_tool("/read console.html"))
        self.assertIsNone(parse_easy_tool("/pwd"))
        self.assertIsNone(parse_easy_tool("/git"))
        self.assertIsNone(parse_easy_tool("/list ."))
        self.assertIsNone(parse_easy_tool("/grep foo"))


class TestOperatorWriteDispatch(_WorkspaceTmp):
    def test_slash_read_and_pwd_are_craft_not_live_exec(self):
        from realai.orchestration.v3_orchestrator import _chat_operator_dispatch

        read = _chat_operator_dispatch("/read hello.txt")
        self.assertEqual((read or {}).get("surface"), "craft")
        self.assertNotEqual((read or {}).get("surface"), "live_exec")
        result = (read or {}).get("result") or {}
        self.assertNotIn("need_explicit_command", str(result.get("error") or ""))
        blob = str(result.get("content") or result)
        self.assertIn("alpha-ground-token", blob)

        pwd = _chat_operator_dispatch("/pwd")
        self.assertEqual((pwd or {}).get("surface"), "craft")
        self.assertNotEqual((pwd or {}).get("surface"), "live_exec")
        pwd_res = (pwd or {}).get("result") or {}
        self.assertTrue(pwd_res.get("ok") or pwd_res.get("workspace") or pwd_res.get("banner"), pwd_res)

    def test_slash_write_runs_craft_tool_write_not_live_exec(self):
        from realai.orchestration.v3_orchestrator import _chat_operator_dispatch

        rel = "docs/recovery/_auditor_probe.txt"
        dispatch = _chat_operator_dispatch(f"/write {rel} PROBE_OK")
        self.assertIsNotNone(dispatch)
        self.assertEqual(dispatch.get("surface"), "craft")
        self.assertNotEqual(dispatch.get("surface"), "live_exec")
        result = dispatch.get("result") or {}
        self.assertTrue(result.get("ok"), result)
        self.assertEqual(result.get("craft_action"), "write")
        written = (self.root / rel).read_text(encoding="utf-8")
        self.assertEqual(written, "PROBE_OK")

    def test_craft_write_alias_same_tool(self):
        from realai.orchestration.v3_orchestrator import _operator_intent_dispatch

        rel = "docs/recovery/_craft_alias.txt"
        dispatch = _operator_intent_dispatch(f"/craft write {rel} ALIAS_OK")
        self.assertIsNotNone(dispatch)
        self.assertEqual(dispatch.get("surface"), "craft")
        result = dispatch.get("result") or {}
        self.assertTrue(result.get("ok"), result)
        self.assertEqual((self.root / rel).read_text(encoding="utf-8"), "ALIAS_OK")

    def test_write_pipe_content(self):
        from realai.orchestration.v3_orchestrator import _operator_intent_dispatch

        rel = "docs/pipe.txt"
        dispatch = _operator_intent_dispatch(f"/write {rel}|||\nline-a\nline-b\n")
        result = (dispatch or {}).get("result") or {}
        self.assertTrue(result.get("ok"), result)
        self.assertIn("line-a", (self.root / rel).read_text(encoding="utf-8"))

    def test_write_outside_workspace_fails(self):
        from realai.orchestration.v3_orchestrator import _operator_intent_dispatch

        escape = self.root.parent / "escape.txt"
        if escape.exists():
            escape.unlink()
        dispatch = _operator_intent_dispatch("/write ../escape.txt NOPE")
        result = (dispatch or {}).get("result") or {}
        self.assertTrue(result.get("error") or result.get("ok") is False, result)
        self.assertFalse(escape.exists())


class TestNaturalWriteSpec(unittest.TestCase):
    def test_create_file_extracts_path_and_content(self):
        path, content = extract_write_spec(
            "create file docs/recovery/_auditor_probe.txt with content PROBE_OK"
        )
        self.assertEqual(path, "docs/recovery/_auditor_probe.txt")
        self.assertEqual(content, "PROBE_OK")
        self.assertTrue(
            looks_like_write_ask(
                "create file docs/recovery/_auditor_probe.txt with content PROBE_OK"
            )
        )
        plans = plan_natural_write(
            "create file docs/recovery/_auditor_probe.txt with content PROBE_OK"
        )
        self.assertEqual(plans[0][0], "write")
        self.assertEqual(plans[0][1]["path"], "docs/recovery/_auditor_probe.txt")
        self.assertEqual(plans[0][1]["content"], "PROBE_OK")

    def test_write_to_path(self):
        path, content = extract_write_spec(
            "write PROBE_OK to docs/recovery/_auditor_probe.txt"
        )
        self.assertEqual(path, "docs/recovery/_auditor_probe.txt")
        self.assertEqual(content, "PROBE_OK")

    def test_inspect_only_is_not_a_write_plan(self):
        self.assertFalse(looks_like_write_ask("what's in console.html"))
        self.assertFalse(looks_like_write_ask("read hello.txt"))
        self.assertEqual(plan_natural_write("what's in hello.txt"), [])
        self.assertTrue(looks_like_patch_ask("fix the login bug in hello.txt"))
        self.assertFalse(looks_like_write_ask("fix the login bug in hello.txt"))


class TestNaturalCreateFileWrites(_WorkspaceTmp):
    def test_create_file_with_path_and_content_writes(self):
        rel = "docs/recovery/_auditor_probe.txt"
        ask = f"create file {rel} with content PROBE_OK"
        body = {"messages": [{"role": "user", "content": ask}]}
        meta = apply_natural_grounding(body, ask)
        self.assertTrue(meta.get("should_ground"))
        self.assertTrue(meta.get("wrote"), meta)
        self.assertIn("write", meta.get("used_tools") or [])
        self.assertTrue(meta.get("short_circuit"))
        self.assertFalse(meta.get("admit_failure"), meta)
        self.assertEqual((self.root / rel).read_text(encoding="utf-8"), "PROBE_OK")

    def test_inspect_only_does_not_write(self):
        before = {p.relative_to(self.root) for p in self.root.rglob("*") if p.is_file()}
        ask = "what's in hello.txt"
        body = {"messages": [{"role": "user", "content": ask}]}
        meta = apply_natural_grounding(body, ask)
        self.assertTrue(meta.get("should_ground"))
        self.assertFalse(meta.get("wrote"))
        self.assertNotIn("write", meta.get("used_tools") or [])
        after = {p.relative_to(self.root) for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)
        content = str((body["messages"][-1] or {}).get("content") or "")
        if not meta.get("admit_failure"):
            self.assertIn("alpha-ground-token", content)

    def test_create_without_content_does_not_invent_write(self):
        ask = "create file docs/recovery/_auditor_probe.txt"
        body = {"messages": [{"role": "user", "content": ask}]}
        meta = apply_natural_grounding(body, ask)
        self.assertTrue(meta.get("admit_failure"))
        self.assertFalse(meta.get("wrote"))
        self.assertFalse((self.root / "docs/recovery/_auditor_probe.txt").exists())
        self.assertIn("won't invent", (meta.get("failure_text") or "").lower())

    def test_patch_ask_flags_model_writes_without_inventing(self):
        ask = "fix the login bug in hello.txt"
        body = {"messages": [{"role": "user", "content": ask}]}
        meta = apply_natural_grounding(body, ask)
        self.assertTrue(meta.get("should_ground"))
        self.assertTrue(meta.get("apply_model_writes"), meta)
        self.assertFalse(meta.get("wrote"))
        self.assertEqual(
            (self.root / "hello.txt").read_text(encoding="utf-8"),
            "alpha-ground-token\n",
        )


_CORE_SENTINEL = "# REAL_CORE live_exec — do not clobber\n"
_MISSION_WIPE = (
    "Do this now.\n\n"
    "Mission\n"
    "1. create file realai/bot/live_exec.py with content "
    "THIS IS A TASK PROMPT SCRAP get to work and overwrite the real module\n"
    "2. Then continue with numbered hive steps and more mission prose so this "
    "paste is long enough to look like a multi-step operator dump rather than "
    "an intentional Craft write.\n"
)


class TestProtectedCorePath(unittest.TestCase):
    def test_core_bot_and_orch_and_launcher(self):
        self.assertTrue(is_protected_core_path("realai/bot/live_exec.py"))
        self.assertTrue(is_protected_core_path("realai/bot/natural_mode.py"))
        self.assertTrue(is_protected_core_path("realai/orchestration/v3_orchestrator.py"))
        self.assertTrue(is_protected_core_path("realai/orchestration/nested/foo.py"))
        self.assertTrue(is_protected_core_path("scripts/run_local_chat.ps1"))
        self.assertTrue(is_protected_core_path(r"C:\RealAI-clean\realai\bot\live_exec.py"))
        self.assertFalse(is_protected_core_path("docs/ok.txt"))
        self.assertFalse(is_protected_core_path("realai/docs/note.md"))
        self.assertFalse(is_protected_core_path("apps/vscode/webview/console.html"))


class TestNaturalMissionDoesNotWipeCore(_WorkspaceTmp):
    def _seed_core(self) -> Path:
        target = self.root / "realai" / "bot" / "live_exec.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_CORE_SENTINEL, encoding="utf-8")
        return target

    def test_plan_natural_write_skips_live_exec(self):
        ask = "create file realai/bot/live_exec.py with content MISSION_SCRAP"
        self.assertTrue(looks_like_write_ask(ask))
        path, content = extract_write_spec(ask)
        self.assertEqual(path, "realai/bot/live_exec.py")
        self.assertEqual(content, "MISSION_SCRAP")
        self.assertEqual(plan_natural_write(ask), [])

    def test_mission_paste_does_not_overwrite_live_exec(self):
        target = self._seed_core()
        body = {"messages": [{"role": "user", "content": _MISSION_WIPE}]}
        meta = apply_natural_grounding(body, _MISSION_WIPE)
        self.assertFalse(meta.get("wrote"), meta)
        self.assertTrue(meta.get("admit_failure"), meta)
        self.assertIn("refusing_natural_write_protected_path", meta.get("failure_text") or "")
        self.assertIn("live_exec.py", meta.get("failure_text") or "")
        self.assertEqual(target.read_text(encoding="utf-8"), _CORE_SENTINEL)

    def test_write_to_live_exec_does_not_clobber(self):
        target = self._seed_core()
        ask = 'write "Do this now Mission scrap" to realai/bot/live_exec.py'
        body = {"messages": [{"role": "user", "content": ask}]}
        meta = apply_natural_grounding(body, ask)
        self.assertFalse(meta.get("wrote"), meta)
        self.assertTrue(meta.get("admit_failure"), meta)
        self.assertEqual(target.read_text(encoding="utf-8"), _CORE_SENTINEL)

    def test_docs_write_still_ok(self):
        ask = "create file docs/ok.txt with content hi"
        body = {"messages": [{"role": "user", "content": ask}]}
        meta = apply_natural_grounding(body, ask)
        self.assertTrue(meta.get("wrote"), meta)
        self.assertEqual((self.root / "docs/ok.txt").read_text(encoding="utf-8"), "hi")

    def test_tool_write_refuses_without_allow_protected(self):
        target = self._seed_core()
        result = tool_write("realai/bot/live_exec.py", content="WIPED")
        self.assertFalse(result.get("ok"))
        self.assertIn("refusing_write_protected_path", str(result.get("error") or ""))
        self.assertEqual(target.read_text(encoding="utf-8"), _CORE_SENTINEL)

    def test_tool_write_allow_protected_explicit(self):
        self._seed_core()
        result = tool_write(
            "realai/bot/live_exec.py",
            content="# stub\n",
            allow_protected=True,
        )
        self.assertTrue(result.get("ok"), result)
        self.assertEqual(
            (self.root / "realai/bot/live_exec.py").read_text(encoding="utf-8"),
            "# stub\n",
        )

    def test_model_suggested_write_to_live_exec_refused(self):
        target = self._seed_core()
        reply = "/write realai/bot/live_exec.py|||\nWIPED_BY_CODER\n"
        applied = apply_suggested_writes(reply)
        self.assertEqual(len(applied), 1)
        result = applied[0].get("result") or {}
        self.assertFalse(result.get("ok"), result)
        self.assertIn("refusing_write_protected_path", str(result.get("error") or ""))
        self.assertEqual(target.read_text(encoding="utf-8"), _CORE_SENTINEL)


class TestExplicitWriteProtected(_WorkspaceTmp):
    def test_slash_write_docs_pipe_still_works(self):
        from realai.orchestration.v3_orchestrator import _operator_intent_dispatch

        dispatch = _operator_intent_dispatch("/write docs/ok.txt|||hi")
        result = (dispatch or {}).get("result") or {}
        self.assertTrue(result.get("ok"), result)
        self.assertEqual((self.root / "docs/ok.txt").read_text(encoding="utf-8"), "hi")

    def test_slash_write_protected_pipe_allowed(self):
        from realai.orchestration.v3_orchestrator import _operator_intent_dispatch

        rel = "realai/bot/live_exec.py"
        (self.root / "realai/bot").mkdir(parents=True, exist_ok=True)
        (self.root / rel).write_text(_CORE_SENTINEL, encoding="utf-8")
        dispatch = _operator_intent_dispatch(f"/write {rel}|||# stub")
        result = (dispatch or {}).get("result") or {}
        self.assertTrue(result.get("ok"), result)
        self.assertEqual((self.root / rel).read_text(encoding="utf-8"), "# stub")

    def test_slash_write_protected_without_pipe_refused(self):
        from realai.orchestration.v3_orchestrator import _operator_intent_dispatch

        rel = "realai/bot/live_exec.py"
        (self.root / "realai/bot").mkdir(parents=True, exist_ok=True)
        (self.root / rel).write_text(_CORE_SENTINEL, encoding="utf-8")
        dispatch = _operator_intent_dispatch(
            f"/write {rel} Do this now Mission scrap get to work"
        )
        result = (dispatch or {}).get("result") or {}
        self.assertTrue(result.get("error") or result.get("ok") is False, result)
        self.assertIn("protected", str(result.get("error") or "").lower())
        self.assertEqual((self.root / rel).read_text(encoding="utf-8"), _CORE_SENTINEL)


if __name__ == "__main__":
    unittest.main()
