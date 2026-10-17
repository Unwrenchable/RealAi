"""Local SDXL-Turbo image backend (diffusers + torch-directml). No API keys.

Weights: C:\\models\\image\\sdxl-turbo (override with REALAI_SDXL_DIR).
SDXL-Turbo is licensed under the Stability AI Community License (see LICENSE.md in the weights dir).
"""
from __future__ import annotations

import base64
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

MODEL_DIR = Path(os.environ.get("REALAI_SDXL_DIR", r"C:\models\image\sdxl-turbo"))
OUT_DIR = Path(os.environ.get("REALAI_IMAGE_OUT", r"C:\models\image\out"))
_PIPE = None
_DEV = None
_LOCK = threading.Lock()


def weights_present(model_dir: Optional[Path] = None) -> bool:
    d = Path(model_dir or MODEL_DIR)
    return (d / "model_index.json").is_file() and any((d / "unet").glob("*.safetensors"))


def _device():
    try:
        import torch_directml
        return torch_directml.device()
    except Exception:
        return "cpu"


def load_pipeline():
    global _PIPE, _DEV
    with _LOCK:
        if _PIPE is None:
            import torch
            from diffusers import AutoPipelineForText2Image
            _DEV = _device()
            dtype = torch.float16 if _DEV != "cpu" else torch.float32
            pipe = AutoPipelineForText2Image.from_pretrained(
                str(MODEL_DIR), torch_dtype=dtype, variant="fp16", use_safetensors=True)
            pipe = pipe.to(_DEV)
            pipe.set_progress_bar_config(disable=True)
            # 12 GB card shared with llama-server: keep peaks low
            pipe.enable_attention_slicing()
            pipe.enable_vae_slicing()
            pipe.enable_vae_tiling()
            _PIPE = pipe
    return _PIPE


def _parse_size(size: str) -> tuple[int, int]:
    try:
        w, h = (int(x) for x in str(size).lower().split("x"))
    except Exception:
        w, h = 512, 512
    return max(256, min(w, 1024)) // 8 * 8, max(256, min(h, 1024)) // 8 * 8


def generate(prompt: str, *, size: str = "512x512", steps: int = 1, seed: Optional[int] = None,
             out_path: Optional[str] = None) -> Dict[str, Any]:
    import torch
    t0 = time.time()
    pipe = load_pipeline()
    t_load = time.time() - t0
    w, h = _parse_size(size)
    steps = max(1, min(int(steps or 1), 4))
    gen = torch.Generator("cpu").manual_seed(int(seed)) if seed is not None else None
    t1 = time.time()
    img = pipe(prompt=prompt, num_inference_steps=steps, guidance_scale=0.0,
               width=w, height=h, generator=gen).images[0]
    t_gen = time.time() - t1
    if out_path:
        p = Path(out_path)
    else:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        p = OUT_DIR / f"sdxl_{int(time.time()*1000)}.png"
    p.parent.mkdir(parents=True, exist_ok=True)
    img.save(p)
    return {"ok": True, "path": str(p), "width": w, "height": h, "steps": steps,
            "device": str(_DEV), "load_s": round(t_load, 2), "gen_s": round(t_gen, 2),
            "backend": "sdxl_turbo_local"}


def handle_images_generations(payload: Dict[str, Any]) -> Dict[str, Any]:
    """OpenAI-compatible POST /v1/images/generations body -> response (local only)."""
    prompt = str(payload.get("prompt") or "").strip()
    if not prompt:
        return {"error": {"message": "prompt required", "type": "invalid_request_error"}}
    n = max(1, min(int(payload.get("n") or 1), 4))
    fmt = payload.get("response_format") or "b64_json"
    data = []
    for _ in range(n):
        r = generate(prompt, size=payload.get("size") or "512x512", steps=int(payload.get("steps") or 1))
        if fmt == "b64_json":
            data.append({"b64_json": base64.b64encode(Path(r["path"]).read_bytes()).decode(), "revised_prompt": prompt})
        else:
            data.append({"url": Path(r["path"]).as_uri(), "revised_prompt": prompt})
    return {"created": int(time.time()), "data": data, "backend": "sdxl_turbo_local"}


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser(description="RealAI local SDXL-Turbo")
    ap.add_argument("prompt", nargs="+")
    ap.add_argument("--size", default="512x512")
    ap.add_argument("--steps", type=int, default=1)
    ap.add_argument("--seed", type=int)
    ap.add_argument("--out")
    a = ap.parse_args()
    if not weights_present():
        raise SystemExit(f"SDXL-Turbo weights not found in {MODEL_DIR}")
    print(json.dumps(generate(" ".join(a.prompt), size=a.size, steps=a.steps, seed=a.seed, out_path=a.out), indent=2))
