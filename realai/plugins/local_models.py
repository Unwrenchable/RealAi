"""Compatibility shim for realai.plugins.local_models -> realai.core.local_models (canonical, decision 2).

This copy differed from the canonical only in the LocalModelManager docstring; the canonical now also carries the
PEFT LoRA backend (get_llm, _load_peft_transformers, _generate_peft_transformers) recovered from
imports/promoted/local_models.py. Module object aliased so private names / monkeypatching keep working.
"""
import sys as _sys

from realai.core import local_models as _canonical

_sys.modules[__name__] = _canonical
