"""Sticky operator memory is injected on every Console system prefix."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from realai.bot.boot import (
    HARD_IDENTITY_LOCK,
    _OPERATOR_MEMORY_CHAT_CAP,
    chat_system_prefix,
    load_operator_memory,
    operator_memory_path,
)


def _restore_env(key: str, val):
    if val is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = val


class TestOperatorMemoryLoad(unittest.TestCase):
    def setUp(self):
        prev = os.environ.get("REALAI_OPERATOR_MEMORY_FILE")
        os.environ.pop("REALAI_OPERATOR_MEMORY_FILE", None)
        self.addCleanup(lambda: _restore_env("REALAI_OPERATOR_MEMORY_FILE", prev))

    def test_canonical_file_loads_into_prefix(self):
        path = operator_memory_path()
        self.assertIsNotNone(path)
        self.assertTrue(path.is_file())
        mem = load_operator_memory()
        self.assertIn("REALAI_HOME = C:\\RealAI-clean", mem)
        self.assertIn("live/realai-clean-20260911", mem)
        self.assertIn("realai/orchestration/v3_orchestrator.py", mem)
        self.assertIn("realai/orchestration/v3_runtime_bridge.py", mem)
        self.assertIn("dest-empty shims", mem)
        self.assertIn("No mega-merge", mem)
        self.assertIn("{slug}_learned", mem)
        self.assertIn("fusion-ui/", mem)
        self.assertIn(":8001", mem)
        self.assertLessEqual(len(mem), _OPERATOR_MEMORY_CHAT_CAP)
        self.assertFalse(mem.endswith("…"))

        prefix = chat_system_prefix("")
        self.assertIn(HARD_IDENTITY_LOCK, prefix)
        self.assertIn("Console Operator", prefix)
        self.assertIn("REALAI_HOME = C:\\RealAI-clean", prefix)
        self.assertIn("live/realai-clean-20260911", prefix)
        # Tail fact must survive the directive's 480-char clip.
        self.assertIn("GET /v1/agents stays ~14 hive roles", prefix)
        self.assertIn("rackup_coach", prefix)
        self.assertIn("atomicfizz_coach", prefix)

        with_op = chat_system_prefix(
            "When the user asks about files or code: read/list/grep first — never invent contents."
        )
        self.assertIn("never invent contents", with_op.lower())
        self.assertIn("OPERATOR MEMORY:", with_op)
        self.assertIn("No Fusion tab in Console", with_op)

    def test_env_file_overrides_canonical(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "memory.md"
        path.write_text("OPERATOR MEMORY:\n- token-ZZZ-hive-gold\n", encoding="utf-8")
        os.environ["REALAI_OPERATOR_MEMORY_FILE"] = str(path)
        mem = load_operator_memory()
        self.assertIn("token-ZZZ-hive-gold", mem)
        self.assertNotIn("C:\\RealAI-clean", mem)
        prefix = chat_system_prefix("operator-bit")
        self.assertIn("token-ZZZ-hive-gold", prefix)
        self.assertIn("operator-bit", prefix)
        self.assertIn(HARD_IDENTITY_LOCK, prefix)

    def test_missing_env_file_falls_back_to_canonical(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        os.environ["REALAI_OPERATOR_MEMORY_FILE"] = str(Path(tmp.name) / "missing.md")
        path = operator_memory_path()
        self.assertIsNotNone(path)
        self.assertTrue(str(path).replace("\\", "/").endswith("docs/OPERATOR_MEMORY.md"))
        self.assertIn("REALAI_HOME = C:\\RealAI-clean", load_operator_memory())

    def test_missing_file_is_safe(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        missing = Path(tmp.name) / "no-such-operator-memory.md"
        with patch("realai.bot.boot._ROOT", Path(tmp.name)):
            os.environ["REALAI_OPERATOR_MEMORY_FILE"] = str(missing)
            self.assertIsNone(operator_memory_path())
            self.assertEqual(load_operator_memory(), "")
        with patch("realai.bot.boot.operator_memory_path", return_value=missing):
            self.assertEqual(load_operator_memory(), "")
            prefix = chat_system_prefix("still-here")
        self.assertIn(HARD_IDENTITY_LOCK, prefix)
        self.assertIn("still-here", prefix)
        self.assertNotIn("OPERATOR MEMORY:", prefix)
        self.assertIn("Console Operator", prefix)

    def test_unreadable_file_is_safe(self):
        with patch("realai.bot.boot.operator_memory_path", return_value=Path("docs/OPERATOR_MEMORY.md")):
            with patch.object(Path, "read_text", side_effect=OSError("denied")):
                self.assertEqual(load_operator_memory(), "")
        with patch("realai.bot.boot.load_operator_memory", side_effect=RuntimeError("boom")):
            prefix = chat_system_prefix("")
        self.assertIn(HARD_IDENTITY_LOCK, prefix)
        self.assertIn("EXECUTE", prefix)

    def test_oversize_memory_is_clipped(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "huge.md"
        path.write_text(("M" * 4000) + "ENDMARKER", encoding="utf-8")
        os.environ["REALAI_OPERATOR_MEMORY_FILE"] = str(path)
        mem = load_operator_memory()
        self.assertLessEqual(len(mem), _OPERATOR_MEMORY_CHAT_CAP)
        self.assertTrue(mem.endswith("…"))
        self.assertNotIn("ENDMARKER", mem)
        prefix = chat_system_prefix("")
        self.assertIn(HARD_IDENTITY_LOCK, prefix)
        self.assertNotIn("ENDMARKER", prefix)
        self.assertLess(len(mem), 4000)


if __name__ == "__main__":
    unittest.main()
