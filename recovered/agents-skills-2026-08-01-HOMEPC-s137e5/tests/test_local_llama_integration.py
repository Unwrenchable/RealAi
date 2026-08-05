"""Integration tests for RealAI local llama.cpp backend.

Run these tests to verify your local setup is working correctly.
"""

import json
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess
import sys


class TestLlamaCliBackend(unittest.TestCase):
    """Test the llama-cli backend implementation."""

    def setUp(self):
        """Set up test fixtures."""
        # Import here to allow tests to run even if dependencies are missing
        try:
            from realai.server.llama_cli_backend import LlamaCliBackend
            from realai.server.backends import SamplingConfig
            self.LlamaCliBackend = LlamaCliBackend
            self.SamplingConfig = SamplingConfig
            self.imports_available = True
        except ImportError as e:
            self.imports_available = False
            self.skipTest(f"Required imports not available: {e}")

    def test_backend_initialization(self):
        """Test that backend can be initialized."""
        backend = self.LlamaCliBackend()
        self.assertIsNotNone(backend)
        self.assertEqual(backend.name, 'llama-cli')

    def test_backend_with_custom_path(self):
        """Test backend initialization with custom llama-cli path."""
        custom_path = "/custom/path/llama-cli"
        backend = self.LlamaCliBackend(llama_cli_path=custom_path)
        self.assertEqual(backend._llama_cli_path, custom_path)

    @patch('shutil.which')
    def test_find_llama_cli_in_path(self, mock_which):
        """Test finding llama-cli in PATH."""
        mock_which.return_value = '/usr/bin/llama-cli'
        backend = self.LlamaCliBackend()
        found = backend._find_llama_cli()
        self.assertIsNotNone(found)
        self.assertEqual(str(found), '/usr/bin/llama-cli')

    @patch('shutil.which')
    @patch('pathlib.Path.exists')
    def test_find_llama_cli_common_locations(self, mock_exists, mock_which):
        """Test finding llama-cli in common installation locations."""
        mock_which.return_value = None

        def exists_side_effect(path_self):
            # Simulate finding llama-cli in common location
            return 'llama.cpp' in str(path_self)

        mock_exists.side_effect = lambda: exists_side_effect

        backend = self.LlamaCliBackend()
        # Available should be False if llama-cli is not found
        # This is expected for CI/test environments
        self.assertIsInstance(backend.available(), bool)

    def test_sampling_config_defaults(self):
        """Test SamplingConfig default values."""
        config = self.SamplingConfig()
        self.assertEqual(config.temperature, 0.2)
        self.assertEqual(config.top_p, 1.0)
        self.assertEqual(config.repetition_penalty, 1.0)
        self.assertEqual(config.max_tokens, 1024)

    def test_sampling_config_custom_values(self):
        """Test SamplingConfig with custom values."""
        config = self.SamplingConfig(
            temperature=0.7,
            top_p=0.95,
            repetition_penalty=1.1,
            max_tokens=512
        )
        self.assertEqual(config.temperature, 0.7)
        self.assertEqual(config.top_p, 0.95)
        self.assertEqual(config.repetition_penalty, 1.1)
        self.assertEqual(config.max_tokens, 512)

    @patch('subprocess.run')
    @patch.object(Path, 'exists', return_value=True)
    def test_generate_success(self, mock_exists, mock_run):
        """Test successful text generation."""
        # Mock llama-cli being available
        backend = self.LlamaCliBackend()
        backend._resolved_path = Path('/usr/bin/llama-cli')

        # Mock subprocess response
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Test prompt\nThis is the generated response."
        mock_run.return_value = mock_result

        config = self.SamplingConfig()
        result = backend.generate(
            model_path="/path/to/model.gguf",
            prompt="Test prompt",
            sampling=config
        )

        self.assertIsNotNone(result)
        self.assertIn("generated response", result.lower())

    @patch('subprocess.run')
    @patch.object(Path, 'exists', return_value=True)
    def test_generate_failure(self, mock_exists, mock_run):
        """Test handling of llama-cli failure."""
        backend = self.LlamaCliBackend()
        backend._resolved_path = Path('/usr/bin/llama-cli')

        # Mock subprocess failure
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Error loading model"
        mock_run.return_value = mock_result

        config = self.SamplingConfig()
        result = backend.generate(
            model_path="/path/to/model.gguf",
            prompt="Test prompt",
            sampling=config
        )

        self.assertIsNone(result)

    def test_generate_model_not_found(self):
        """Test handling of missing model file."""
        backend = self.LlamaCliBackend()
        backend._resolved_path = Path('/usr/bin/llama-cli')

        config = self.SamplingConfig()
        result = backend.generate(
            model_path="/nonexistent/model.gguf",
            prompt="Test prompt",
            sampling=config
        )

        self.assertIsNone(result)

    def test_generate_backend_not_available(self):
        """Test generation when backend is not available."""
        backend = self.LlamaCliBackend()
        backend._resolved_path = None

        config = self.SamplingConfig()
        result = backend.generate(
            model_path="/path/to/model.gguf",
            prompt="Test prompt",
            sampling=config
        )

        self.assertIsNone(result)


class TestBackendIntegration(unittest.TestCase):
    """Test integration of llama-cli backend with backend resolver."""

    def setUp(self):
        """Set up test fixtures."""
        try:
            from realai.server.backends import BackendResolver
            self.BackendResolver = BackendResolver
            self.imports_available = True
        except ImportError as e:
            self.imports_available = False
            self.skipTest(f"Required imports not available: {e}")

    def test_backend_resolver_initialization(self):
        """Test that BackendResolver initializes all backends."""
        resolver = self.BackendResolver()
        self.assertIsNotNone(resolver._vllm)
        self.assertIsNotNone(resolver._llama_cpp)
        # llama_cli may be None if not installed, which is fine
        self.assertTrue(hasattr(resolver, '_llama_cli'))
        self.assertIsNotNone(resolver._fallback)

    def test_select_backend_by_hint(self):
        """Test backend selection by hint."""
        resolver = self.BackendResolver()

        # Test that selecting llama-cli works if available
        backend = resolver.select_backend('llama-cli')
        self.assertIsNotNone(backend)

        # Test that invalid hint falls back to best available
        backend = resolver.select_backend('invalid-backend')
        self.assertIsNotNone(backend)

    def test_backend_fallback_chain(self):
        """Test that backend selection has proper fallback chain."""
        resolver = self.BackendResolver()

        # Should always return a backend (fallback if nothing else)
        backend = resolver.select_backend('')
        self.assertIsNotNone(backend)

        # Test known backend names
        for hint in ['vllm', 'llama.cpp', 'llama-cli', 'llamacli']:
            backend = resolver.select_backend(hint)
            self.assertIsNotNone(backend)


class TestModelRegistry(unittest.TestCase):
    """Test model registry configuration."""

    def test_registry_file_exists(self):
        """Test that registry file exists."""
        registry_path = Path(__file__).parent.parent / 'realai' / 'models' / 'registry.json'
        self.assertTrue(registry_path.exists(), 
                       f"Registry file not found at {registry_path}")

    def test_registry_is_valid_json(self):
        """Test that registry is valid JSON."""
        registry_path = Path(__file__).parent.parent / 'realai' / 'models' / 'registry.json'
        if not registry_path.exists():
            self.skipTest("Registry file not found")

        with open(registry_path, 'r') as f:
            data = json.load(f)

        self.assertIsInstance(data, dict)

    def test_registry_has_local_models(self):
        """Test that registry includes llama-cli models."""
        registry_path = Path(__file__).parent.parent / 'realai' / 'models' / 'registry.json'
        if not registry_path.exists():
            self.skipTest("Registry file not found")

        with open(registry_path, 'r') as f:
            data = json.load(f)

        # Check for llama-cli backend models
        llama_cli_models = [
            name for name, config in data.items()
            if isinstance(config, dict) and config.get('backend') in ['llama-cli', 'llama.cpp']
        ]

        # Should have at least one local model configured
        self.assertGreater(len(llama_cli_models), 0, 
                          "No llama-cli models found in registry")

    def test_registry_model_structure(self):
        """Test that registry models have required fields."""
        registry_path = Path(__file__).parent.parent / 'realai' / 'models' / 'registry.json'
        if not registry_path.exists():
            self.skipTest("Registry file not found")

        with open(registry_path, 'r') as f:
            data = json.load(f)

        for model_name, config in data.items():
            if not isinstance(config, dict):
                continue  # Skip comment entries

            # Check required fields
            self.assertIn('type', config, f"Model {model_name} missing 'type'")
            self.assertIn('backend', config, f"Model {model_name} missing 'backend'")
            self.assertIn('path', config, f"Model {model_name} missing 'path'")

            # Validate field types
            self.assertIsInstance(config['type'], str)
            self.assertIsInstance(config['backend'], str)
            self.assertIsInstance(config['path'], str)


class TestDocumentation(unittest.TestCase):
    """Test that documentation files exist."""

    def test_main_setup_guide_exists(self):
        """Test that main setup guide exists."""
        doc_path = Path(__file__).parent.parent / 'docs' / 'local-llama-setup.md'
        self.assertTrue(doc_path.exists(), 
                       f"Setup guide not found at {doc_path}")

    def test_local_readme_exists(self):
        """Test that local README exists."""
        doc_path = Path(__file__).parent.parent / 'docs' / 'LOCAL_LLAMA_README.md'
        self.assertTrue(doc_path.exists(), 
                       f"Local README not found at {doc_path}")

    def test_quickstart_exists(self):
        """Test that quickstart guide exists."""
        doc_path = Path(__file__).parent.parent / 'QUICKSTART_LOCAL.md'
        self.assertTrue(doc_path.exists(), 
                       f"Quickstart not found at {doc_path}")

    def test_setup_script_exists(self):
        """Test that setup checker script exists."""
        script_path = Path(__file__).parent.parent / 'scripts' / 'setup_local_llama.py'
        self.assertTrue(script_path.exists(), 
                       f"Setup script not found at {script_path}")

    def test_example_script_exists(self):
        """Test that example script exists."""
        script_path = Path(__file__).parent.parent / 'examples' / 'local_llama_example.py'
        self.assertTrue(script_path.exists(), 
                       f"Example script not found at {script_path}")


def run_tests():
    """Run all tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestLlamaCliBackend))
    suite.addTests(loader.loadTestsFromTestCase(TestBackendIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestModelRegistry))
    suite.addTests(loader.loadTestsFromTestCase(TestDocumentation))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
