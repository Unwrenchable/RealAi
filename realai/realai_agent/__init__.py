"""
RealAI Agent Package
"""

from typing import Optional
from langchain_openai import ChatOpenAI
import os

__version__ = "1.0.0"

# Lazy-loaded LLM
_llm: Optional[ChatOpenAI] = None

def get_llm() -> ChatOpenAI:
    """Get the LLM instance, initializing it if necessary."""
    global _llm
    if _llm is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # Return a mock LLM for testing
            from unittest.mock import MagicMock
            _llm = MagicMock()
            _llm.invoke = MagicMock(return_value="Mock response")
        else:
            model_name = os.getenv("REALAI_MODEL", "meta-llama/Llama-3.1-70B-Instruct")
            temperature = float(os.getenv("REALAI_TEMPERATURE", "0.0"))
            _llm = ChatOpenAI(model=model_name, temperature=temperature)
    return _llm

# Lazy imports to avoid initialization issues
def _import_main():
    from .main import realai_ultimate
    return realai_ultimate

def _import_hierarchical_agent():
    from .hierarchical_agent import hierarchical_agent
    return hierarchical_agent

def _import_supervisor():
    from .supervisor import supervisor
    return supervisor

def _import_agents():
    from .agents import AGENT_REGISTRY
    return AGENT_REGISTRY

def _import_rise_system():
    from .rise_system import rise_system
    return rise_system

def _import_tools():
    from .tools import TOOL_REGISTRY
    return TOOL_REGISTRY

def _import_training_pipeline():
    from .training_pipeline import training_pipeline
    return training_pipeline

# Expose lazy-loaded properties
realai_ultimate = property(_import_main)
hierarchical_agent = property(_import_hierarchical_agent)
supervisor = property(_import_supervisor)
AGENT_REGISTRY = property(_import_agents)
rise_system = property(_import_rise_system)
TOOL_REGISTRY = property(_import_tools)
training_pipeline = property(_import_training_pipeline)

__version__ = "1.0.0"