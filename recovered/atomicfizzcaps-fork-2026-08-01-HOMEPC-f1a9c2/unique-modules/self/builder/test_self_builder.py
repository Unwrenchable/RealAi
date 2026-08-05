"""Self-builder parsing and repo tools."""

from unittest import TestCase

from realai.agent_protocol import ParsedAction, parse_agent_reply as protocol_parse
from realai.repo_tools import read_file, workspace_root
from realai.self_builder import parse_agent_reply as legacy_parse  # the 3-tuple shim


class TestSelfBuilder(TestCase):
    def test_legacy_tuple_parse(self):
        text = 'TOOL: read_file\nARGS: {"target_file": "README.md", "limit": 5}'
        tool, args, done = legacy_parse(text)
        self.assertEqual(tool, "read_file")
        self.assertEqual(args.get("target_file"), "README.md")
        self.assertIsNone(done)

    def test_protocol_rich_parse(self):
        action: ParsedAction = protocol_parse('TOOL: search_replace\nARGS: {"file_path": "x.py"}')
        self.assertTrue(action.tool)
        self.assertEqual(action.args.get("file_path"), "x.py")
        self.assertIsNone(action.done)

    def test_parse_done(self):
        _, _, done = legacy_parse("DONE: Added tests and docs.")
        self.assertEqual(done, "Added tests and docs.")

    def test_parse_done_with_llama_prefix(self):
        _, _, done = legacy_parse(": DONE: tests pass")
        self.assertEqual(done, "tests pass")

    def test_read_readme(self):
        path = workspace_root() / "README.md"
        if not path.exists():
            self.skipTest("README missing")
        result = read_file("README.md", limit=3)
        self.assertIn("content", result)
        self.assertGreater(result.get("total_lines", 0), 0)