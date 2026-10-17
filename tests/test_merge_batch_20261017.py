"""Lower-priority family merges (2026-10-17). Static checks: these are training/runtime scripts that run at import."""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _defs(rel):
    t = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
    names = {n.name for n in ast.walk(t) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    names |= {g.id for n in t.body if isinstance(n, ast.Assign) for g in n.targets if isinstance(g, ast.Name)}
    return names


def test_train_lora_local_package_copy_is_union_with_product_root_runner():
    pkg, root = _defs("realai/scripts/train_lora_local.py"), _defs("scripts/train_lora_local.py")
    assert root <= pkg and "_resume_vulkan_stack" in pkg
    src = (ROOT / "realai/scripts/train_lora_local.py").read_text(encoding="utf-8")
    assert "--resume-vulkan" in src and "--no-resume-vulkan" in src and "from vulkan_runtime import pause_vulkan" in src


def test_vulkan_runtime_package_copy_has_job_object_safe_start():
    src = (ROOT / "realai/scripts/vulkan_runtime.py").read_text(encoding="utf-8")
    assert "Win32_Process" in src and "start_new_session=True" in src
    assert _defs("scripts/vulkan_runtime.py") <= _defs("realai/scripts/vulkan_runtime.py")


def test_train_qwen_directml_grad_accum_default_preserves_behaviour():
    src = (ROOT / "realai/core/training/train_qwen_lora_directml.py").read_text(encoding="utf-8")
    assert 'os.environ.get("TRAIN_GRADIENT_ACCUMULATION_STEPS", "1")' in src
    assert "(loss / GRAD_ACCUM).backward()" in src and "if micro % GRAD_ACCUM:" in src
    ast.parse(src)
