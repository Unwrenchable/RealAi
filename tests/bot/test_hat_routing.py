"""Automated hat routing for Natural Mode. No Core-desk toggle."""
from __future__ import annotations

import os
import unittest
from pathlib import Path

from realai.bot.boot import chat_system_prefix
from realai.bot.hat_routing import (
    HATS,
    hat_turn_prefix,
    infer_hat,
    normalize_hat,
    raw_diagnostic_appendix,
)
from realai.bot.natural_mode import (
    MAX_TOOLS_THIS_TURN,
    apply_natural_grounding,
    format_operator_reply,
    format_write_verified_reply,
    plan_natural_turn,
)


ROOT = Path(__file__).resolve().parents[2]


class TestInferHat(unittest.TestCase):
    def test_only_four_hats(self):
        self.assertEqual(HATS, ("Hive", "One-tree", "Builder", "RackUp"))
        prompts = [
            "what's the hive health",
            "read console.html",
            "fix the login bug",
            "smoke GET /health",
            "",
            "hello",
            "something vague about Tuesday",
        ]
        for prompt in prompts:
            self.assertIn(infer_hat(prompt), HATS, prompt)
        self.assertEqual(normalize_hat("Wizard"), "One-tree")
        self.assertEqual(normalize_hat("rack up"), "RackUp")
        self.assertEqual(normalize_hat(""), "One-tree")

    def test_hive_prompts(self):
        for prompt in (
            "what's the hive health",
            "show orchestration topology",
            "learn queue depth",
            "how many agents are live",
            "what's broken",
            "audit the hive",
            "system state of the overseer",
        ):
            self.assertEqual(infer_hat(prompt), "Hive", prompt)

    def test_one_tree_prompts(self):
        for prompt in (
            "what's in this repo",
            "read console.html",
            "grep for workspace_read",
            "where is v3_orchestrator.py",
            "read realai/orchestration/v3_orchestrator.py",
            "list the workspace files",
            "scan the codebase",
        ):
            self.assertEqual(infer_hat(prompt), "One-tree", prompt)

    def test_builder_prompts(self):
        for prompt in (
            "fix the hive health check",
            "refactor realai/bot/natural_mode.py",
            "generate a patch for the console",
            "propose a css change for console.html",
            "create file docs/note.txt with content hi",
            "implement the missing handler",
        ):
            self.assertEqual(infer_hat(prompt), "Builder", prompt)

    def test_rackup_prompts(self):
        for prompt in (
            "smoke GET /health",
            "deploy and validate the API",
            "run the tests against the endpoint",
            "curl http://127.0.0.1:8001/health",
            "hit the health endpoint",
        ):
            self.assertEqual(infer_hat(prompt), "RackUp", prompt)

    def test_ambiguous_prefers_one_tree_for_readonly_inspect(self):
        # Noun collisions (smoke, agents, orchestration) lose to a real read.
        for prompt in (
            "",
            "hello",
            "read the smoke test in tests/bot/test_natural_mode.py",
            "grep agents in the repo",
            "what's in realai/orchestration/v3_orchestrator.py",
            "audit this repo",
            "audit console.html",
        ):
            self.assertEqual(infer_hat(prompt), "One-tree", prompt)

    def test_write_verb_beats_hive_and_rackup(self):
        self.assertEqual(infer_hat("fix the hive health check"), "Builder")
        self.assertEqual(infer_hat("patch the health endpoint and smoke it"), "Builder")
        self.assertEqual(infer_hat("fix the endpoint then smoke it"), "Builder")

    def test_smoke_action_beats_a_supporting_read(self):
        # A smoke verb is an action. "read the smoke test" stays One-tree.
        self.assertEqual(infer_hat("smoke the hive and read console.html"), "RackUp")
        self.assertEqual(infer_hat("read the smoke test"), "One-tree")

    def test_coach_is_not_the_rackup_hat(self):
        self.assertEqual(infer_hat("give me a rackup coach practice plan"), "One-tree")
        self.assertNotEqual(infer_hat("atomicfizz coach wrist hint"), "RackUp")
        # A real HTTP verb still selects RackUp even if Coach is named.
        self.assertEqual(infer_hat("smoke the rackup coach API"), "RackUp")

    def test_grounding_dump_does_not_flip_the_hat(self):
        ask = "read console.html"
        dumped = ask + "\n\nTool results\nsmoke GET /health hive agents fix the file"
        self.assertEqual(infer_hat(dumped), "One-tree")


class TestHatInPrefixAndReply(unittest.TestCase):
    def test_prefix_names_inferred_hat_and_keeps_caps(self):
        text = chat_system_prefix("", user_text="what's the hive health")
        self.assertIn("Mode Active: Hive", text)
        self.assertIn("Tool bias this turn:", text)
        self.assertIn("diagnostics", text)
        self.assertIn("Summary:", text)
        self.assertIn("MAX_TOOLS_THIS_TURN=3", text)
        self.assertIn("180s", text)
        self.assertIn("LANDED", text)
        self.assertIn("Console Operator", text)
        self.assertIn("Service Unavailable", text)

    def test_explicit_hat_overrides_prompt(self):
        text = chat_system_prefix("operator-bit", user_text="read console.html", hat="RackUp")
        self.assertIn("Mode Active: RackUp", text)
        self.assertIn("HTTP client", text)
        self.assertNotIn("Mode Active: One-tree", text)

    def test_empty_call_does_not_invent_a_turn_hat(self):
        text = chat_system_prefix("")
        # The standing contract names the four hats. A specific Mode Active
        # line is only added once a prompt or hat is supplied.
        self.assertIn("Mode Active: Hive | One-tree | Builder | RackUp", text)
        self.assertNotIn("Tool bias this turn:", text)

    def test_reply_card_coexists_with_legacy_contract(self):
        reply = format_operator_reply(
            summary="Read console.html.",
            changed="none",
            verify="PASS read",
            nxt="Ask for a change.",
            hat="One-tree",
        )
        self.assertTrue(reply.startswith("Mode Active: One-tree"))
        self.assertIn("Action Taken:", reply)
        self.assertIn("Key Results:", reply)
        self.assertIn("Next Recommended Step:", reply)
        self.assertIn("Summary:", reply)
        self.assertIn("What changed:", reply)
        self.assertIn("Verify:", reply)
        self.assertIn("\nNext:", reply)
        self.assertNotIn("LANDED", reply)

    def test_smoke_down_is_service_unavailable_and_folded(self):
        reply = format_write_verified_reply(
            {"ok": True, "path": "notes/desk.txt", "bytes": 5},
            {"path": "notes/desk.txt", "content": "hello\n", "total_lines": 1},
            {
                "ok": False,
                "url": "http://127.0.0.1:8001/health",
                "error": "URLError: [Errno 111] Connection refused",
                "post_step": True,
            },
            hat="Builder",
        )
        self.assertIn("Mode Active: Builder", reply)
        self.assertIn("hive smoke failed", reply)
        self.assertIn("Service Unavailable", reply)
        self.assertIn("FAIL", reply)
        self.assertNotIn("smoke passed", reply)
        self.assertNotIn("LANDED", reply.split("--- on disk", 1)[0])
        self.assertNotIn("SHIPPED", reply.split("--- on disk", 1)[0])
        # The exception stays out of the card and inside the folded payload.
        card, _, raw = reply.partition("<details>")
        self.assertNotIn("Connection refused", card)
        self.assertIn("Connection refused", raw)
        self.assertIn("View raw diagnostic payload", reply)

    def test_unearned_shipped_is_proposed(self):
        from realai.bot.natural_mode import finalize_natural_choice_text

        shaped, smoke = finalize_natural_choice_text(
            "SHIPPED the patch in app.py",
            {"should_ground": True, "used_tools": ["read"], "hat": "Builder"},
            applied=[],
        )
        self.assertIn("Mode Active: Builder", shaped)
        self.assertIn("PROPOSED", shaped)
        self.assertNotIn("SHIPPED", shaped)
        self.assertNotIn("LANDED", shaped)
        self.assertIsNone(smoke)

    def test_named_path_plan_and_cap_stay(self):
        self.assertEqual(MAX_TOOLS_THIS_TURN, 3)
        plans = plan_natural_turn("propose a css change for console.html")
        self.assertEqual([name for name, _ in plans], ["workspace_read"])
        self.assertEqual(plans[0][1]["path"], "apps/vscode/webview/console.html")
        self.assertEqual(infer_hat("propose a css change for console.html"), "Builder")
        # Hat bias is guidance. It does not spend a fourth tool or skip the read.
        self.assertLessEqual(len(plans), MAX_TOOLS_THIS_TURN)
        self.assertIn("workspace_read", hat_turn_prefix("One-tree"))
        self.assertIn("propose", hat_turn_prefix("Builder").lower())

    def test_grounding_records_hat_and_bias(self):
        body = {"messages": [{"role": "user", "content": "what's in this repo"}]}
        meta = apply_natural_grounding(body, "what's in this repo")
        self.assertEqual(meta.get("hat"), "One-tree")
        if meta.get("should_ground") and not meta.get("admit_failure"):
            content = str((body["messages"][-1] or {}).get("content") or "")
            self.assertIn("Mode Active: One-tree", content)
            self.assertIn("Tool bias this turn:", content)
            self.assertIn("Never say LANDED", content)

    def test_appendix_helper(self):
        block = raw_diagnostic_appendix('{"error": "boom"}')
        self.assertIn("<details>", block)
        self.assertIn("View raw diagnostic payload", block)
        self.assertIn("boom", block)
        self.assertEqual(raw_diagnostic_appendix("  "), "")


class TestConsoleHasNoHatToggle(unittest.TestCase):
    def test_twins_match_and_core_desk_has_no_hat_control(self):
        gold = (ROOT / "apps" / "vscode" / "webview" / "console.html").read_text(encoding="utf-8")
        twin = (ROOT / "console.html").read_text(encoding="utf-8")
        self.assertEqual(gold, twin)
        self.assertIn('id="coreDesk"', gold)
        for token in (
            'data-core="read"',
            'data-core="write"',
            'data-core="git-status"',
            'data-core="hive-health"',
            'data-core="git-diff"',
            'data-core="hive-chat"',
            'data-core="learn"',
        ):
            self.assertIn(token, gold)
        self.assertNotIn("data-hat", gold)
        self.assertNotIn("hat-pill", gold)
        self.assertNotIn("Mode Active", gold.split('id="coreDesk"', 1)[1].split("</div>", 1)[0])
        self.assertIn("View raw diagnostic payload", gold)
        self.assertIn("function renderBubble", gold)
        self.assertIn("Service Unavailable", gold)


class TestOrchestratorHatHook(unittest.TestCase):
    def test_enrich_puts_hat_on_the_system_prefix(self):
        from realai.orchestration.v3_orchestrator import _enrich_chat_body

        body = _enrich_chat_body(
            {
                "messages": [{"role": "user", "content": "smoke GET /health"}],
                "realai_hat": "RackUp",
            }
        )
        self.assertEqual(body.get("realai_hat"), "RackUp")
        system = body["messages"][0]["content"]
        self.assertIn("Mode Active: RackUp", system)
        self.assertIn("MAX_TOOLS_THIS_TURN=3", system)
        # Live hive size stays a standing fact, not a catalog dump.
        self.assertIn("GET /v1/agents stays", system)


class TestDirectiveMentionsHats(unittest.TestCase):
    def test_directive_and_memory(self):
        prev = os.environ.pop("REALAI_OPERATOR_SYSTEM_FILE", None)

        def _restore() -> None:
            if prev is None:
                os.environ.pop("REALAI_OPERATOR_SYSTEM_FILE", None)
            else:
                os.environ["REALAI_OPERATOR_SYSTEM_FILE"] = prev

        self.addCleanup(_restore)
        from realai.bot.boot import load_operator_directive, load_operator_memory

        text = load_operator_directive()
        self.assertIn("Reply contract", text)
        self.assertIn("Mode Active", text)
        self.assertIn("One-tree", text)
        self.assertIn("RackUp", text)
        self.assertIn("MAX_TOOLS_THIS_TURN=3", text)
        self.assertIn("atomic_fizz_hive_client", text)
        self.assertIn("No hat pills", text)
        memory = load_operator_memory()
        self.assertIn("No Core-desk hat toggle", memory)
        self.assertIn("rackup_coach", memory)
        self.assertLessEqual(len(memory), 900)


if __name__ == "__main__":
    unittest.main()
