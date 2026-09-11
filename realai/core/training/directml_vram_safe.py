"""
Universal DirectML / AMD VRAM-safe training patch for RealAI.

Drop-in for Qwen2/2.5, LLaMA 2/3, Mistral/Mixtral, Gemma, Yi, Phi, StarCoder,
Falcon, GPT-J/NeoX-style HF causal LMs.

Usage:
    from core.training.directml_vram_safe import apply_directml_vram_safe, prepare_batch

    apply_directml_vram_safe(model, backend="directml")
    batch = prepare_batch(batch, max_length=64, backend="directml")

What it does:
  - forces float32 model + config dtype
  - disables gradient checkpointing + KV cache
  - patches causal-mask builders to float32 + finite fill (no -inf / uint8 overflow)
  - clamps sequence length before forward
  - coerces attention_mask dtypes safely
  - optional VRAM auto-detect → suggested max_length / lora_r
  - logs dtype + mask shapes
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import torch

log = logging.getLogger("realai.directml_vram_safe")

# Finite fill DirectML accepts (avoids -inf → uint8 overflow)
_SAFE_FILL = -1.0e4

_PATCHED = False
_LOGGED_BATCH = False


@dataclass
class VramPlan:
    max_length: int
    lora_r: int
    batch_size: int
    dtype: torch.dtype
    notes: str


def detect_vram_gb() -> Optional[float]:
    """Best-effort VRAM detect (CUDA). DirectML has no reliable API — return None."""
    try:
        if torch.cuda.is_available():
            props = torch.cuda.get_device_properties(0)
            return float(props.total_memory) / (1024**3)
    except Exception:
        pass
    # AMD DirectML: allow env override
    import os

    env = os.environ.get("REALAI_VRAM_GB", "").strip()
    if env:
        try:
            return float(env)
        except ValueError:
            pass
    return None


def suggest_vram_plan(
    backend: str,
    model_name: str = "",
    vram_gb: Optional[float] = None,
) -> VramPlan:
    """
    Suggest safe train hyperparams for the GPU.
    Defaults assume RX 6700 XT-class 12GB when DirectML and unknown VRAM.
    """
    name = (model_name or "").lower()
    backend = (backend or "").lower()
    vram = vram_gb if vram_gb is not None else detect_vram_gb()
    if backend == "directml" and vram is None:
        vram = float(__import__("os").environ.get("REALAI_VRAM_GB") or 12.0)

    dtype = torch.float16 if backend == "cuda" else torch.float32

    # Size bucket from model id
    if any(x in name for x in ("70b", "65b", "34b", "32b")):
        size = "huge"
    elif any(x in name for x in ("13b", "14b", "7b", "8b", "9b")):
        size = "large"
    elif any(x in name for x in ("3b", "4b", "2.7b", "2b", "1.5b", "1b")):
        size = "medium"
    else:
        size = "small"  # 0.5B etc.

    if backend == "cpu":
        return VramPlan(64 if size != "small" else 128, 8, 1, torch.float32, "cpu fallback")

    if vram is not None and vram <= 8:
        table = {
            "huge": (32, 2, 1),
            "large": (32, 2, 1),
            "medium": (64, 4, 1),
            "small": (128, 8, 1),
        }
    elif vram is not None and vram <= 12:
        table = {
            "huge": (32, 2, 1),
            "large": (64, 4, 1),
            "medium": (64, 8, 1),
            "small": (128, 16, 1),
        }
    else:
        table = {
            "huge": (64, 4, 1),
            "large": (128, 8, 1),
            "medium": (128, 16, 1),
            "small": (256, 16, 1),
        }

    ml, r, bs = table[size]
    # DirectML is stricter than CUDA for masks/activations
    if backend == "directml":
        ml = min(ml, 64 if size in {"large", "huge", "medium"} else 128)
        r = min(r, 8 if size != "small" else 16)
        dtype = torch.float32

    return VramPlan(
        max_length=ml,
        lora_r=r,
        batch_size=bs,
        dtype=dtype,
        notes=f"backend={backend} vram_gb={vram} size={size}",
    )


def _safe_causal_mask_fn(
    attention_mask: torch.Tensor,
    sequence_length: int,
    target_length: int,
    dtype: torch.dtype,
    device: torch.device,
    min_dtype: float,
    cache_position: torch.Tensor,
    batch_size: int,
):
    """DirectML-safe 4D causal mask (float32, finite fill, torch.where)."""
    dtype = torch.float32
    fill = _SAFE_FILL
    if attention_mask is not None and attention_mask.dim() == 4:
        out = attention_mask.to(dtype=dtype)
        log.debug("mask passthrough 4d shape=%s dtype=%s", tuple(out.shape), out.dtype)
        return out

    causal_mask = torch.full(
        (sequence_length, target_length),
        fill_value=fill,
        dtype=dtype,
        device=device,
    )
    if sequence_length != 1:
        causal_mask = torch.triu(causal_mask, diagonal=1)
    causal_mask = causal_mask * (
        torch.arange(target_length, device=device) > cache_position.reshape(-1, 1)
    ).to(dtype)
    causal_mask = causal_mask[None, None, :, :].expand(batch_size, 1, -1, -1)

    if attention_mask is not None:
        causal_mask = causal_mask.clone()
        mask_length = attention_mask.shape[-1]
        am = attention_mask.to(device=device, dtype=dtype)
        padding_mask = am[:, None, None, :] == 0
        slice_ = causal_mask[:, :, :, :mask_length]
        causal_mask[:, :, :, :mask_length] = torch.where(
            padding_mask,
            torch.full_like(slice_, fill),
            slice_,
        )

    log.debug(
        "mask built shape=%s dtype=%s fill=%s seq=%s tgt=%s",
        tuple(causal_mask.shape),
        causal_mask.dtype,
        fill,
        sequence_length,
        target_length,
    )
    return causal_mask


def patch_hf_causal_mask_builders() -> int:
    """
    Monkeypatch known HF causal-mask helpers across model families.
    Returns number of modules patched.
    """
    global _PATCHED
    modules = [
        "transformers.models.qwen2.modeling_qwen2",
        "transformers.models.qwen2_vl.modeling_qwen2_vl",
        "transformers.models.llama.modeling_llama",
        "transformers.models.mistral.modeling_mistral",
        "transformers.models.mixtral.modeling_mixtral",
        "transformers.models.gemma.modeling_gemma",
        "transformers.models.gemma2.modeling_gemma2",
        "transformers.models.phi.modeling_phi",
        "transformers.models.phi3.modeling_phi3",
        "transformers.models.falcon.modeling_falcon",
        "transformers.models.gpt_neox.modeling_gpt_neox",
        "transformers.models.gptj.modeling_gptj",
        "transformers.models.starcoder2.modeling_starcoder2",
        "transformers.models.yi.modeling_yi",
        "transformers.modeling_attn_mask_utils",
    ]
    patched = 0
    import importlib

    for mod_name in modules:
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue
        # Common helper names across recent transformers
        for attr in (
            "_prepare_4d_causal_attention_mask_with_cache_position",
            "_prepare_4d_causal_attention_mask",
            "prepare_4d_causal_attention_mask",
        ):
            if hasattr(mod, attr):
                setattr(mod, attr, _safe_causal_mask_fn)
                patched += 1
                log.info("patched %s.%s", mod_name, attr)
        # Some trees nest helpers inside AttentionMaskConverter
        conv = getattr(mod, "AttentionMaskConverter", None)
        if conv is not None:
            for attr in (
                "_make_causal_mask",
                "_expand_mask",
            ):
                if hasattr(conv, attr):
                    # wrap classmethod/static carefully — skip if signature unknown
                    pass

    # Also patch llama helper used by many copies
    try:
        import transformers.modeling_attn_mask_utils as mask_utils

        if hasattr(mask_utils, "_prepare_4d_causal_attention_mask"):
            # Different signature — wrap to coerce dtype on return
            _orig = mask_utils._prepare_4d_causal_attention_mask

            def _wrap(*a, **k):
                out = _orig(*a, **k)
                if isinstance(out, torch.Tensor):
                    return out.to(dtype=torch.float32)
                return out

            mask_utils._prepare_4d_causal_attention_mask = _wrap
            patched += 1
    except Exception:
        pass

    _PATCHED = patched > 0
    return patched


def apply_directml_vram_safe(
    model: Any,
    *,
    backend: str = "directml",
    force_fp32: bool = True,
) -> Dict[str, Any]:
    """
    Apply universal safe settings on a loaded HF/PEFT model.
    Call AFTER from_pretrained / get_peft_model, BEFORE first forward.
    """
    info: Dict[str, Any] = {"backend": backend, "patched_modules": 0}

    if backend == "directml":
        info["patched_modules"] = patch_hf_causal_mask_builders()

    # Disable KV cache (training)
    try:
        model.config.use_cache = False
        info["use_cache"] = False
    except Exception as e:
        info["use_cache_error"] = str(e)

    # Disable gradient checkpointing on DirectML
    if backend == "directml":
        for fn_name in ("gradient_checkpointing_disable",):
            fn = getattr(model, fn_name, None)
            if callable(fn):
                try:
                    fn()
                    info["gradient_checkpointing"] = "disabled"
                except Exception as e:
                    info["gradient_checkpointing_error"] = str(e)
        # Also clear flag if present
        try:
            if hasattr(model, "is_gradient_checkpointing"):
                model.is_gradient_checkpointing = False
        except Exception:
            pass
    else:
        info["gradient_checkpointing"] = "left_default"

    # Eager attention on DirectML
    if backend == "directml":
        try:
            model.config._attn_implementation = "eager"
            info["attn_implementation"] = "eager"
        except Exception as e:
            info["attn_error"] = str(e)

    # Force fp32
    if force_fp32 and backend in {"directml", "cpu"}:
        try:
            model.config.torch_dtype = torch.float32
        except Exception:
            pass
        try:
            model.to(dtype=torch.float32)
            info["model_dtype"] = "float32"
        except Exception as e:
            info["model_dtype_error"] = str(e)

    if hasattr(model, "enable_input_require_grads"):
        try:
            model.enable_input_require_grads()
            info["input_require_grads"] = True
        except Exception as e:
            info["input_require_grads_error"] = str(e)

    model.train()
    log.info("apply_directml_vram_safe: %s", info)
    print(f"[vram-safe] applied: {info}", flush=True)
    return info


def clamp_batch(
    batch: Dict[str, torch.Tensor],
    max_length: int,
) -> Dict[str, torch.Tensor]:
    """Clamp sequence length BEFORE forward to prevent VRAM spikes."""
    if "input_ids" not in batch:
        return batch
    seq = int(batch["input_ids"].shape[1])
    if seq <= max_length:
        return batch
    out = {}
    for k, v in batch.items():
        if torch.is_tensor(v) and v.dim() >= 2 and v.shape[1] == seq:
            out[k] = v[:, :max_length].contiguous()
        else:
            out[k] = v
    log.debug("clamped seq %s → %s", seq, max_length)
    return out


def prepare_batch(
    batch: Dict[str, torch.Tensor],
    *,
    max_length: int,
    backend: str,
    device: Any,
    log_shapes: bool = True,
) -> Dict[str, torch.Tensor]:
    """
    Universal pre-forward batch prep:
      clamp length → move device → coerce mask dtypes → log shapes
    """
    global _LOGGED_BATCH
    batch = clamp_batch(batch, max_length)
    batch = {k: (v.to(device) if torch.is_tensor(v) else v) for k, v in batch.items()}

    if "attention_mask" in batch and torch.is_tensor(batch["attention_mask"]):
        # Keep 0/1 integer mask for HF APIs; causal patch converts internally.
        am = batch["attention_mask"]
        if backend == "directml":
            batch["attention_mask"] = am.to(dtype=torch.long)
        if log_shapes and not _LOGGED_BATCH:
            print(
                f"[vram-safe] batch input_ids={tuple(batch['input_ids'].shape)} "
                f"mask={tuple(batch['attention_mask'].shape)} "
                f"mask_dtype={batch['attention_mask'].dtype} "
                f"labels_dtype={batch.get('labels').dtype if 'labels' in batch else None}",
                flush=True,
            )
            _LOGGED_BATCH = True

    return batch


def forward_with_oom_backoff(
    model: Any,
    batch: Dict[str, torch.Tensor],
    *,
    max_length: int,
    backend: str,
    device: Any,
    min_length: int = 32,
) -> Any:
    """
    Forward with dynamic sequence shrink on OOM / DirectML overflow.
    """
    cur_len = max_length
    last_err: Optional[Exception] = None
    while cur_len >= min_length:
        b = prepare_batch(batch, max_length=cur_len, backend=backend, device=device, log_shapes=(cur_len == max_length))
        try:
            return model(**b)
        except RuntimeError as e:
            last_err = e
            msg = str(e).lower()
            shrink = (
                "out of memory" in msg
                or "not enough gpu" in msg
                or "uint8" in msg
                or "overflow" in msg
                or "allocate tensor" in msg
            )
            if not shrink:
                raise
            new_len = max(min_length, cur_len // 2)
            print(
                f"[vram-safe] forward failed ({type(e).__name__}: {e}); "
                f"backoff max_length {cur_len} → {new_len}",
                flush=True,
            )
            cur_len = new_len
            if backend == "directml":
                try:
                    import gc

                    gc.collect()
                except Exception:
                    pass
    assert last_err is not None
    raise last_err
