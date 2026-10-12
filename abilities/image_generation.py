"""Image generation - local only. SDXL-Turbo (diffusers/DirectML) when weights exist, Pillow procedural fallback.

No external API keys. The old xAI path is disabled.
"""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "image_generation",
    "name": "image_generation",
    "type": "ability",
    "status": "LIVE",
    "source": "realai.local_sdxl (SDXL-Turbo) -> realai.local_media (Pillow fallback)",
    "dest": "abilities/image_generation.py",
    "capabilities": ["image", "images/generations", "sdxl_turbo_local", "local_pillow"],
    "secrets_policy": "none - fully local, no API keys",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    prompt = str(ctx.get("prompt") or input or "").strip()
    if not prompt:
        return {"ok": False, "error": "prompt_required", "ability": "image_generation"}
    size = str(ctx.get("size") or "512x512")
    backend = str(ctx.get("backend") or "auto").lower()
    sdxl_err = None

    if backend in {"auto", "sdxl", "sdxl_turbo", "local"}:
        try:
            from realai import local_sdxl

            if local_sdxl.weights_present():
                r = local_sdxl.generate(
                    prompt, size=size, steps=int(ctx.get("steps") or 1),
                    seed=ctx.get("seed"), out_path=ctx.get("out_path"),
                )
                return {"ok": True, "ability": "image_generation", "prompt": prompt,
                        "result": r, "source": "sdxl_turbo_local", "local": True}
            sdxl_err = "sdxl_weights_missing"
        except Exception as e:  # fall back to Pillow
            sdxl_err = f"{type(e).__name__}: {e}"

    from realai.local_media import generate_image_local

    local = generate_image_local(prompt, size=size)
    return {
        "ok": bool(local.get("ok")),
        "ability": "image_generation",
        "prompt": prompt,
        "result": local,
        "source": "local_pillow",
        "local": True,
        "live_path": "POST /v1/tools/execute ability.image_generation (local PNG)",
        "sdxl_note": sdxl_err,
    }
