"""Image generation — local Pillow first; optional xAI only if keyed."""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "image_generation",
    "name": "image_generation",
    "type": "ability",
    "status": "LIVE",
    "source": "realai.local_media (+ optional xai_media)",
    "dest": "abilities/image_generation.py",
    "capabilities": ["image", "images/generations", "local_pillow"],
    "secrets_policy": "none required — XAI_API_KEY optional upgrade only",
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

    prefer_cloud = str(ctx.get("backend") or "").lower() in {"xai", "grok", "cloud"}
    if prefer_cloud:
        try:
            from realai.providers import xai_media

            if xai_media.has_api_key():
                result = xai_media.generate_image(
                    prompt,
                    model=ctx.get("model"),
                    n=int(ctx.get("n") or 1),
                    size=ctx.get("size"),
                )
                return {
                    "ok": True,
                    "ability": "image_generation",
                    "prompt": prompt,
                    "result": result,
                    "source": "xai_media",
                    "local": False,
                }
        except Exception as e:
            cloud_err = str(e)
        else:
            cloud_err = "xai_api_key_missing"
    else:
        cloud_err = None

    from realai.local_media import generate_image_local

    local = generate_image_local(prompt, size=str(ctx.get("size") or "512x512"))
    return {
        "ok": bool(local.get("ok")),
        "ability": "image_generation",
        "prompt": prompt,
        "result": local,
        "source": "local_pillow",
        "local": True,
        "live_path": "POST /v1/tools/execute ability.image_generation (local PNG)",
        "cloud_note": cloud_err,
    }
