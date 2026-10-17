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


def test_frontend_drops_failed_turns_helper_merged():
    src = (ROOT / "frontend/lib/realai.ts").read_text(encoding="utf-8")
    assert "export function buildCompletionMessages(" in src and "buildCompletionMessages(messages.slice(0, -1), last)" in src
    assert "export type MessageRole = Role;" in (ROOT / "frontend/lib/types.ts").read_text(encoding="utf-8")


def test_world_model_belief_keys_drop_leading_article_from_git_branch():
    from realai.world_model import BeliefUpdater, Observation, WorldState

    st = WorldState()
    BeliefUpdater().update(st, Observation(id="o1", content="The sky is blue. door = open."))
    assert st.get_fact("sky") == "blue" and st.get_fact("door") == "open"
    assert BeliefUpdater._normalize_key("An Apple") == "apple" and BeliefUpdater._normalize_key("theory") == "theory"


def test_shadowed_shims_resolve_to_canonical():
    import realai.engine as eng
    import realai.world_model as wm
    from realai.core import engine as core_engine

    assert wm.BeliefUpdater.__module__ == "realai._world_model_canonical"
    pub = [n for n in vars(core_engine) if not n.startswith("_") and callable(getattr(core_engine, n))]
    assert pub and getattr(eng, pub[0]) is getattr(core_engine, pub[0])
    assert eng.RECOVERY_STATUS == "missing_source"


def test_extractor_code_and_memory_pairs_recovered_from_git(tmp_path):
    import json

    from realai.core.training import extract_from_agent_tools as ex

    src = tmp_path / "in"
    src.mkdir()
    (src / "fix.patch").write_text("--- a\n+++ b\n", encoding="utf-8")
    (src / "agent_memory.jsonl").write_text(json.dumps({"content": "long talk", "summary": "short"}) + "\n", encoding="utf-8")
    (src / "run_log.json").write_text(json.dumps({"prompt": "hi", "response": "yo"}), encoding="utf-8")
    out = ex.extract_code_and_memory_pairs(src, tmp_path / "out")
    assert out["code_pairs"]["rows"] == 1 and out["memory_pairs"]["rows"] == 1
    assert ex._instruction_examples(ex._collect_records(src))[0]["messages"][1]["content"] == "yo"
    assert not (tmp_path / "out" / "instructions.jsonl").exists()
