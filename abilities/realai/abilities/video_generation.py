"""Video generation — Atomic Fizz xAI Imagine Video client."""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "video_generation",
    "name": "video_generation",
    "type": "ability",
    "status": "PARTIAL",
    "source": "realai.providers.xai_media + Atomic Fizz backend/lib/grok.js",
    "dest": "abilities/video_generation.py",
    "capabilities": ["video", "grok-imagine-video"],
    "secrets_policy": "uses XAI_API_KEY/GROK_API_KEY from env only — never vault keys/",
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
        return {"ok": False, "error": "prompt_required", "ability": "video_generation"}

    from realai.providers import xai_media

    st = xai_media.status()
    if not st.get("api_key_configured"):
        try:
            from abilities.desktop_lambda_video import run as lambda_run

            wrapped = lambda_run(input=prompt, context={**ctx, "prompt": prompt})
        except Exception as e:
            wrapped = {"ok": False, "error": str(e)}
        return {
            "ok": False,
            "ability": "video_generation",
            "error": "xai_api_key_missing",
            "hint": "Set XAI_API_KEY to call api.x.ai /v1/videos/generations (Atomic Fizz grok.js path)",
            "source": "ATOMIC-FIZZ scripts/test_video_generation.js + backend/lib/grok.js",
            "delegate_inventory": wrapped,
            "status": st,
        }

    try:
        result = xai_media.generate_video(
            prompt,
            model=ctx.get("model"),
            duration=int(ctx.get("duration") or 6),
            aspect=str(ctx.get("aspect") or "16:9"),
            resolution=str(ctx.get("resolution") or "720p"),
        )
        return {
            "ok": True,
            "ability": "video_generation",
            "prompt": prompt,
            "result": result,
            "source": "xai_media",
        }
    except Exception as e:
        return {"ok": False, "ability": "video_generation", "error": str(e), "prompt": prompt}
