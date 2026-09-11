"""Video generation — local animated GIF first; optional xAI only if keyed."""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "video_generation",
    "name": "video_generation",
    "type": "ability",
    "status": "LIVE",
    "source": "realai.local_media (+ optional xai_media)",
    "dest": "abilities/video_generation.py",
    "capabilities": ["video", "gif", "local_pillow"],
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
        return {"ok": False, "error": "prompt_required", "ability": "video_generation"}

    prefer_cloud = str(ctx.get("backend") or "").lower() in {"xai", "grok", "cloud"}
    cloud_err = None
    if prefer_cloud:
        try:
            from realai.providers import xai_media

            if xai_media.has_api_key():
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
                    "local": False,
                }
        except Exception as e:
            cloud_err = str(e)
        else:
            cloud_err = "xai_api_key_missing"

    from realai.local_media import generate_video_local

    local = generate_video_local(
        prompt,
        frames=int(ctx.get("frames") or 12),
        size=str(ctx.get("size") or "320x240"),
    )
    return {
        "ok": bool(local.get("ok")),
        "ability": "video_generation",
        "prompt": prompt,
        "result": local,
        "source": "local_pillow_gif",
        "local": True,
        "live_path": "POST /v1/tools/execute ability.video_generation (local GIF)",
        "cloud_note": cloud_err,
    }
