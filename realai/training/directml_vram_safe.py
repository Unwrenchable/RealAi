"""Re-export universal DirectML VRAM-safe patch."""

from core.training.directml_vram_safe import (  # noqa: F401
    VramPlan,
    apply_directml_vram_safe,
    clamp_batch,
    detect_vram_gb,
    forward_with_oom_backoff,
    patch_hf_causal_mask_builders,
    prepare_batch,
    suggest_vram_plan,
)
