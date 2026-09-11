"""Model assets and registry helpers for RealAI."""

from realai.model_registry import CAPABILITY_GRAPH, MODEL_REGISTRY, CapabilityGraph
from realai.server.config import get_model_config, list_models, load_registry

try:
    from realai.local_models import LocalModelManager, LocalModelType, get_llm_engine, get_model_manager
except ImportError:
    from local_models import LocalModelManager, LocalModelType, get_llm_engine, get_model_manager

__all__ = [
    'CAPABILITY_GRAPH',
    'CapabilityGraph',
    'LocalModelManager',
    'LocalModelType',
    'MODEL_REGISTRY',
    'get_llm_engine',
    'get_model_config',
    'get_model_manager',
    'list_models',
    'load_registry',
]
