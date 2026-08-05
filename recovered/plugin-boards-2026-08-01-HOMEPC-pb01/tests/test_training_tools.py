"""Tests for training/export tooling."""

from pathlib import Path
from unittest import TestCase

from realai.training.export_gguf import default_output_name, weights_dir_for
from realai.training.llama_tools import find_llama_cli, find_llama_quantize, repo_root


class TestTrainingTools(TestCase):
    def test_default_output_name(self):
        self.assertEqual(
            default_output_name("realai-1.0-instruct", "Q4_K_M"),
            "realai-1.0-instruct-Q4_K_M.gguf",
        )

    def test_weights_dir_under_models(self):
        path = weights_dir_for("realai-1.0-instruct")
        self.assertTrue(str(path).endswith("realai-1.0-instruct/weights") or "realai-1.0-instruct\\weights" in str(path))

    def test_vendor_llama_quantize_discovered(self):
        quant = find_llama_quantize()
        vendor = repo_root() / "vendor" / "llama.cpp" / "b4400" / "llama-quantize.exe"
        if vendor.is_file():
            self.assertIsNotNone(quant)
            self.assertTrue(quant.name.startswith("llama-quantize"))
        else:
            self.skipTest("vendored llama-quantize.exe not present")

    def test_vendor_llama_cli_discovered(self):
        cli = find_llama_cli()
        vendor = repo_root() / "vendor" / "llama.cpp" / "b4400" / "llama-cli.exe"
        if vendor.is_file():
            self.assertIsNotNone(cli)
        else:
            self.skipTest("vendored llama-cli.exe not present")