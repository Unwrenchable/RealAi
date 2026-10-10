"""RealAI SFT dataset builder (gold: realai/training/dataset_builder/).

Extends the existing builders instead of replacing them:
  * row conversion from ``realai/scripts/wire_training.py`` (row_to_text / iter_jsonl)
  * session conversion from ``realai.training.extract_from_agent_tools.sessions_to_instruction_samples``
  * 90/10 seeded split idea from ``realai/training/build_datasets.py``

Pipeline: source adapters -> Qwen chat ``messages`` -> secret/PII scrub -> length filter
-> exact + near (MinHash) dedupe -> stratified held-out split -> train/eval/manifest under
REALAI_HOME/datasets/<name>-<date>/. Offline by default; never writes outside REALAI_HOME.

CLI: python -m realai.training.dataset_builder --config cfg.json [--dry-run]
"""
from .pipeline import BuildResult, build, load_config, realai_home  # noqa: F401

__all__ = ["BuildResult", "build", "load_config", "realai_home"]
