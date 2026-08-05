"""Unit tests for the strict agent protocol (the solid core of local self-build)."""

from unittest import TestCase

from realai.agent_protocol import ParsedAction, build_system_prompt, normalize_repo_args, parse_agent_reply


class TestAgentProtocol(TestCase):
    def test_build_prompt_has_rules_and_examples(self):
        p = build_system_prompt("/tmp/ws")
        self.assertIn("CRITICAL INSTRUCTIONS", p)
        self.assertIn("TOOL:", p)
        self.assertIn("DONE:", p)
        self.assertIn("read_file", p)

    def test_parse_tool_classic(self):
        a = parse_agent_reply('TOOL: read_file\nARGS: {"target_file": "foo.py", "limit": 10}')
        self.assertIsInstance(a, ParsedAction)
        self.assertEqual(a.tool, "read_file")
        self.assertEqual(a.args["target_file"], "foo.py")

    def test_parse_json_fenced(self):
        text = '```json\n{"tool": "grep", "args": {"pattern": "def "}}\n```'
        a = parse_agent_reply(text)
        self.assertEqual(a.tool, "grep")
        self.assertIn("pattern", a.args)

    def test_parse_done_variants(self):
        self.assertEqual(parse_agent_reply("DONE: All tests green.").done, "All tests green.")
        self.assertEqual(parse_agent_reply(": DONE: self-build tests pass").done, "self-build tests pass")

    def test_normalize_aliases(self):
        self.assertEqual(normalize_repo_args("read_file", {"file_path": "x.py"})["target_file"], "x.py")
        self.assertEqual(normalize_repo_args("search_replace", {"target_file": "y.py"})["file_path"], "y.py")

    def test_bad_input_gives_none(self):
        a = parse_agent_reply("I decided to just chat instead of using the format.")
        self.assertIsNone(a.tool)
        self.assertIsNone(a.done)