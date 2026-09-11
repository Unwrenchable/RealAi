"""Training pipeline helpers for RealAI."""

from realai.identity import PersonaTrainer
from realai.self_improvement import PerformanceEvaluator, TrainingDataGenerator, VersionManager

from .build_datasets import build_dataset_bundle
from .eval import evaluate_instruction_dataset
from .extract_from_agent_tools import extract_agent_tool_data
from .finetune import build_finetune_plan

__all__ = [
    'PerformanceEvaluator',
    'PersonaTrainer',
    'TrainingDataGenerator',
    'VersionManager',
    'build_dataset_bundle',
    'build_finetune_plan',
    'evaluate_instruction_dataset',
    'extract_agent_tool_data',
]
