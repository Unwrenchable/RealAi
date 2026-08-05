"""Unit tests for local structured-server backends."""

from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from realai.server.backends import BackendResolver, SamplingConfig
from realai.server.config import get_model_config, list_models
from realai.server.llama_cli_backend import LlamaCliBackend


class TestLlamaCliBackend(TestCase):
    def test_backend_initialization(self):
        backend = LlamaCliBackend()
        self.assertEqual(backend.name, 'llama-cli')

    def test_backend_with_custom_path(self):
        backend = LlamaCliBackend(llama_cli_path='/custom/path/llama-cli')
        self.assertEqual(backend._llama_cli_path, '/custom/path/llama-cli')

    @patch('shutil.which')
    def test_find_llama_cli_in_path(self, mock_which):
        mock_which.return_value = '/usr/bin/llama-cli'
        backend = LlamaCliBackend()
        found = backend._find_llama_cli()
        self.assertEqual(found, Path('/usr/bin/llama-cli'))

    def test_sampling_config_defaults(self):
        config = SamplingConfig()
        self.assertEqual(config.temperature, 0.2)
        self.assertEqual(config.top_p, 1.0)
        self.assertEqual(config.repetition_penalty, 1.0)
        self.assertEqual(config.max_tokens, 1024)

    @patch('subprocess.run')
    @patch.object(Path, 'exists', return_value=True)
    def test_generate_success(self, _mock_exists, mock_run):
        backend = LlamaCliBackend()
        backend._resolved_path = Path('/usr/bin/llama-cli')

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = 'Test prompt\nThis is the generated response.'
        mock_run.return_value = mock_result

        result = backend.generate('/path/to/model.gguf', 'Test prompt', SamplingConfig())
        self.assertIn('generated response', result.lower())

    @patch('subprocess.run')
    @patch.object(Path, 'exists', return_value=True)
    def test_generate_failure(self, _mock_exists, mock_run):
        backend = LlamaCliBackend()
        backend._resolved_path = Path('/usr/bin/llama-cli')

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = 'Error loading model'
        mock_run.return_value = mock_result

        result = backend.generate('/path/to/model.gguf', 'Test prompt', SamplingConfig())
        self.assertIsNone(result)


class TestBackendIntegration(TestCase):
    def test_backend_resolver_initialization(self):
        resolver = BackendResolver()
        self.assertIsNotNone(resolver._fallback)
        self.assertTrue(hasattr(resolver, '_llama_cli'))

    def test_backend_selection_returns_backend(self):
        resolver = BackendResolver()
        for hint in ['vllm', 'llama.cpp', 'llama-cli', 'llamacli', 'invalid']:
            backend = resolver.select_backend(hint)
            self.assertIsNotNone(backend)


class TestModelRegistry(TestCase):
    def test_registry_lists_default_models(self):
        models = list_models()
        self.assertIn('realai-1.0', models)
        self.assertIn('realai-embed', models)

    def test_registry_model_structure(self):
        chat_model = get_model_config('realai-1.0')
        embed_model = get_model_config('realai-embed')

        self.assertEqual(chat_model['type'], 'chat')
        self.assertEqual(embed_model['type'], 'embedding')
        self.assertEqual(embed_model['backend'], 'deterministic')
