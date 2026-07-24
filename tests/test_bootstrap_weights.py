"""Bootstrap native weights from existing Q4 GGUF."""

from pathlib import Path
from unittest import TestCase

from realai.model_assets import resolve_realai_gguf, repo_root
from realai.training.bootstrap_weights import discover_local_gguf


class TestBootstrapWeights(TestCase):
    def test_discover_finds_repo_gguf(self):
        discovered = discover_local_gguf()
        root_gguf = repo_root() / "models" / "Llama-3.2-1B-Instruct-Q4_K_M.gguf"
        if not root_gguf.exists():
            self.skipTest("reference GGUF not in repo")
        names = {p.name for p in discovered}
        self.assertIn(root_gguf.name, names)

    def test_instruct_weights_ready_after_bootstrap(self):
        gguf, diag = resolve_realai_gguf("realai-1.0-instruct")
        if gguf is None:
            self.skipTest("run bootstrap_weights first")
        self.assertEqual(diag.get("status"), "ready")
        self.assertTrue(gguf.name.startswith("realai-1.0-instruct"))