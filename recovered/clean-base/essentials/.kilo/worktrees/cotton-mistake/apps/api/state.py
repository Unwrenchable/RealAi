"""Shared runtime state for API routes and app startup."""

import os

from core.inference.local_stub import LocalStubChat, LocalStubEmbeddings
from core.inference.registry import InferenceRegistry
from core.models.cache import ModelCache
from core.tools.code import CodeExecutionTool
from core.tools.file import FileTool
from core.tools.registry import ToolRegistry
from core.tools.web import WebSearchTool
from core.tools.web3 import Web3Tool
from core.voice.asr_whisper import WhisperASR
from core.voice.registry import VoiceRegistry
from core.voice.tts_piper import PiperTTS
from core.web3.evm_backend import EVMBackend
from core.web3.policy import Web3Policy
from core.web3.registry import Web3Registry
from core.web3.solana_backend import SolanaBackend


model_cache = ModelCache()

inference_registry = InferenceRegistry()
inference_registry.register_chat("realai-default", LocalStubChat())
inference_registry.register_chat("realai-1.0", LocalStubChat())
inference_registry.register_chat("realai-2.0", LocalStubChat())
inference_registry.register_embed("realai-embed-default", LocalStubEmbeddings())
inference_registry.register_embed("realai-embed", LocalStubEmbeddings())

tool_registry = ToolRegistry()
tool_registry.register(WebSearchTool())
tool_registry.register(CodeExecutionTool())
tool_registry.register(FileTool("."))

web3_registry = Web3Registry()
web3_policy = Web3Policy()
web3_registry.register(SolanaBackend())
evm_rpc_url = os.getenv("REALAI_EVM_RPC_URL", "").strip()
if evm_rpc_url:
    try:
        web3_registry.register(EVMBackend(evm_rpc_url, private_key=os.getenv("REALAI_EVM_PRIVATE_KEY")))
    except Exception:
        pass
tool_registry.register(Web3Tool(web3_registry, policy=web3_policy))

voice_registry = VoiceRegistry()
voice_registry.register_asr(WhisperASR())
voice_registry.register_tts(PiperTTS())
