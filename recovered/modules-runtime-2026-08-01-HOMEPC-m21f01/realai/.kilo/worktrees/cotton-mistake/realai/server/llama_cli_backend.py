"""Llama CLI backend for local GGUF model inference via llama-cli.exe."""

import json
import subprocess
import shutil
from pathlib import Path
from typing import Optional

from .backends import InferenceBackend, SamplingConfig
from .logging_utils import setup_logging

logger = setup_logging()


class LlamaCliBackend(InferenceBackend):
    """Backend that calls llama-cli.exe for local inference with GGUF models.

    This backend provides a lightweight alternative to llama-cpp-python by
    directly invoking the llama-cli executable, avoiding Python binding
    compilation and allowing users to use pre-built llama.cpp binaries.
    """

    name = 'llama-cli'

    def __init__(self, llama_cli_path: Optional[str] = None):
        """Initialize the llama-cli backend.

        Args:
            llama_cli_path: Path to llama-cli.exe. If None, searches in PATH.
        """
        self._llama_cli_path = llama_cli_path
        self._resolved_path: Optional[Path] = None

    def _find_llama_cli(self) -> Optional[Path]:
        """Find llama-cli executable in PATH or configured location."""
        if self._llama_cli_path:
            path = Path(self._llama_cli_path)
            if path.exists():
                return path
            logger.warning('Configured llama-cli path does not exist: %s', path)
            return None

        # Try common executable names
        for name in ['llama-cli', 'llama-cli.exe', 'llama']:
            found = shutil.which(name)
            if found:
                return Path(found)

        # Try common installation locations on Windows
        common_paths = [
            Path.home() / 'llama.cpp' / 'build' / 'bin' / 'Release' / 'llama-cli.exe',
            Path.home() / 'llama.cpp' / 'llama-cli.exe',
            Path('C:/llama.cpp/llama-cli.exe'),
            Path('C:/Program Files/llama.cpp/llama-cli.exe'),
        ]
        for path in common_paths:
            if path.exists():
                return path

        return None

    def available(self) -> bool:
        """Check if llama-cli is available."""
        if self._resolved_path is None:
            self._resolved_path = self._find_llama_cli()
        return self._resolved_path is not None

    def generate(self, model_path: str, prompt: str, sampling: SamplingConfig) -> Optional[str]:
        """Generate text using llama-cli.exe.

        Args:
            model_path: Path to GGUF model file
            prompt: Input prompt text
            sampling: Sampling configuration

        Returns:
            Generated text or None on failure
        """
        if not self.available():
            logger.error('llama-cli backend not available')
            return None

        model_file = Path(model_path)
        if not model_file.exists():
            logger.error('Model file not found: %s', model_path)
            return None

        # Build command line arguments
        cmd = [
            str(self._resolved_path),
            '--model', str(model_file),
            '--prompt', prompt,
            '--n-predict', str(sampling.max_tokens),
            '--temp', str(sampling.temperature),
            '--top-p', str(sampling.top_p),
            '--repeat-penalty', str(sampling.repetition_penalty),
            '--log-disable',  # Disable llama.cpp internal logging
            '--simple-io',  # Use simple I/O mode for easier parsing
        ]

        try:
            logger.info('Invoking llama-cli: %s', ' '.join(cmd[:4]))  # Log first few args
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                encoding='utf-8',
                errors='replace'
            )

            if result.returncode != 0:
                logger.error('llama-cli failed with code %d: %s', result.returncode, result.stderr)
                return None

            # Parse output - llama-cli with --simple-io outputs the generated text
            output = result.stdout.strip()

            # Remove the prompt echo if present
            if output.startswith(prompt):
                output = output[len(prompt):].lstrip()

            return output

        except subprocess.TimeoutExpired:
            logger.error('llama-cli timed out after 300 seconds')
            return None
        except Exception as exc:
            logger.error('llama-cli execution failed: %s', exc)
            return None


class LlamaCliChatBackend(LlamaCliBackend):
    """Chat-optimized llama-cli backend with message formatting.

    This variant formats chat messages with proper templates before
    calling llama-cli, providing better chat model compatibility.
    """

    name = 'llama-cli-chat'

    def generate(self, model_path: str, prompt: str, sampling: SamplingConfig) -> Optional[str]:
        """Generate chat response with proper message formatting.

        The prompt should already be formatted by the inference layer,
        but we can add additional chat-specific processing here if needed.
        """
        # For now, delegate to parent - future enhancement could add
        # chat template detection and application
        return super().generate(model_path, prompt, sampling)


def create_llama_cli_backend(config: Optional[dict] = None) -> LlamaCliBackend:
    """Factory function to create a llama-cli backend from configuration.

    Args:
        config: Optional configuration dict with keys:
            - llama_cli_path: Path to llama-cli executable
            - chat_mode: If True, returns LlamaCliChatBackend

    Returns:
        Configured LlamaCliBackend or LlamaCliChatBackend
    """
    if config is None:
        config = {}

    llama_cli_path = config.get('llama_cli_path')
    chat_mode = config.get('chat_mode', False)

    if chat_mode:
        return LlamaCliChatBackend(llama_cli_path=llama_cli_path)
    return LlamaCliBackend(llama_cli_path=llama_cli_path)
