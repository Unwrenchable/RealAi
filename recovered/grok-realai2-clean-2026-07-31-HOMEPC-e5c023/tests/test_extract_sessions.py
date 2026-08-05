"""Training ingest from self-builder sessions."""

import json
import tempfile
from pathlib import Path
from unittest import TestCase

from realai.training.extract_from_agent_tools import (
    extract_all_training_sources,
    sessions_to_instruction_samples,
)


class TestExtractSessions(TestCase):
    def test_sessions_to_samples(self):
        sessions = [
            {
                "task": "fix tests",
                "result": {"summary": "ok", "trace": [{"tool": "run_terminal_command", "args": {"command": "echo 1"}}]},
            }
        ]
        out = sessions_to_instruction_samples(sessions)
        self.assertEqual(len(out), 1)
        self.assertIn("fix tests", out[0]["messages"][0]["content"])

    def test_extract_writes_instructions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sessions = root / "self_builder_sessions.jsonl"
            sessions.write_text(
                json.dumps({"task": "ping", "messages": [{"role": "user", "content": "ping"}, {"role": "assistant", "content": "pong"}]})
                + "\n",
                encoding="utf-8",
            )
            result = extract_all_training_sources(output_root=root)
            self.assertGreaterEqual(result["rows"], 1)
            self.assertTrue((root / "instructions.jsonl").is_file())