"""Tests for RealAI native GGUF resolution."""

from pathlib import Path
from unittest import TestCase

from realai.model_assets import (
    is_realai_owned_model,
    resolve_realai_gguf,
    repo_root,
)


class TestModelAssets(TestCase):
    def test_realai_owned_detection(self):
        self.assertTrue(is_realai_owned_model("realai-1.0", {"owned_by": "realai"}))
        self.assertFalse(is_realai_owned_model("realai-embed", {"owned_by": "realai"}))
        self.assertFalse(is_realai_owned_model("qwen-coder-7b", {"owned_by": "reference"}))

    def test_resolve_dev_reference_gguf(self):
        path = repo_root() / "models" / "Llama-3.2-1B-Instruct-Q4_K_M.gguf"
        if not path.exists():
            self.skipTest("dev GGUF not present")
        resolved, diag = resolve_realai_gguf("llama-local-1b", str(path))
        self.assertIsNotNone(resolved)
        self.assertEqual(diag.get("status"), "ready")

    def test_realai_1_0_missing_weights(self):
        gguf, diag = resolve_realai_gguf("realai-1.0")
        if gguf is not None:
            self.assertTrue(gguf.suffix == ".gguf")
        else:
            self.assertEqual(diag.get("status"), "missing")
            self.assertIn("expected_paths", diag)