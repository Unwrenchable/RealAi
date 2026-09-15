"""Console empty-state layout + encoding smoke (no browser required)."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONSOLE_FILES = (
    ROOT / "console.html",
    ROOT / "apps" / "vscode" / "webview" / "console.html",
)


class TestConsoleLayoutSmoke(unittest.TestCase):
    def test_both_copies_identical_and_ascii(self):
        bodies = [p.read_bytes() for p in CONSOLE_FILES]
        self.assertTrue(all(p.is_file() for p in CONSOLE_FILES))
        self.assertEqual(bodies[0], bodies[1], "console.html copies drifted")
        raw = bodies[0]
        self.assertFalse(any(b > 127 for b in raw), "console.html must stay ASCII-safe")
        text = raw.decode("ascii")
        self.assertIn('<meta charset="UTF-8"', text)
        self.assertIn('placeholder="Ask anything."', text)
        self.assertIn("Advanced - optional dock", text)
        self.assertNotIn("Advanced �", text)
        self.assertNotIn("\ufffd", text)

    def test_collapsed_advanced_is_single_chat_column(self):
        text = CONSOLE_FILES[0].read_text(encoding="ascii")
        self.assertIn('class="app no-ops"', text)
        self.assertIn(".app.no-ops > .ops{display:none !important}", text)
        self.assertIn('grid-template-areas: "rail stage"', text)
        self.assertIn('grid-template-areas: "rail stage ops"', text)
        self.assertIn(".scrim{", text)
        self.assertIn("position:absolute", text)
        # scrim must not steal a grid column
        self.assertIn("grid-area:rail", text.replace(" ", ""))
        self.assertIn("used tools:", text)
        self.assertIn("I'll use tools, abilities, and agents when needed.", text)
        self.assertIn('data-p="audit this repo"', text)
        self.assertIn('data-p="learn from this folder"', text)
        self.assertIn('data-p="what\'s broken"', text)
