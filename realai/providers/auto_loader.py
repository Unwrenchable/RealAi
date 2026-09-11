import json
from pathlib import Path
from realai.providers.custom_model_provider import RealAICustomModelProvider

REGISTRY = r"D:\models\checkpoints_lora\realai_model_registry_stub.json"

def load_custom_provider():
    print("[RealAI AutoLoader] Loading custom provider...")
    provider = RealAICustomModelProvider(REGISTRY)
    return provider.load()
