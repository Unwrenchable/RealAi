"""Image analysis — prefer xAI vision (Atomic Fizz / Grok); fall back to client scaffold."""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "image_analysis",
    "name": "image_analysis",
    "type": "ability",
    "status": "PARTIAL",
    "source": "realai.providers.xai_media.analyze_image + core.agents.tools.image_processor",
    "dest": "abilities/image_analysis.py",
    "capabilities": ["vision", "image_analysis", "multimodal"],
    "secrets_policy": "uses XAI_API_KEY/GROK_API_KEY from env only",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    image_url = str(ctx.get("image_url") or ctx.get("url") or input or "").strip()
    action = str(ctx.get("action") or "analyze").lower()
    prompt = str(
        ctx.get("prompt")
        or "Describe this image in detail. List notable objects, style, and any text."
    )
    if not image_url:
        return {"ok": False, "error": "image_url_required", "ability": "image_analysis"}

    from realai.providers import xai_media

    if xai_media.has_api_key():
        try:
            result = xai_media.analyze_image(image_url, prompt=prompt, model=ctx.get("model"))
            return {
                "ok": True,
                "ability": "image_analysis",
                "action": action,
                "image_url": image_url,
                "result": result,
                "placeholder": False,
                "source": "xai_vision",
            }
        except Exception as e:
            vision_err = str(e)
    else:
        vision_err = "xai_api_key_missing"

    from core.agents.tools import image_processor

    raw = image_processor(image_url, action=action)
    parsed: Any = raw
    if isinstance(raw, str):
        try:
            import json

            parsed = json.loads(raw)
        except Exception:
            parsed = {"raw": raw}

    placeholder = True
    if isinstance(parsed, dict):
        desc = str(parsed.get("description") or "")
        if "Detailed general analysis of the image" in desc or parsed.get("ok") is False:
            placeholder = True
        elif parsed.get("description") and vision_err == "xai_api_key_missing":
            placeholder = "Detailed general analysis" in str(parsed.get("description"))

    return {
        "ok": True,
        "ability": "image_analysis",
        "action": action,
        "image_url": image_url,
        "result": parsed,
        "placeholder": placeholder,
        "xai_error": vision_err,
        "note": (
            "Set XAI_API_KEY for real Grok vision analysis (Atomic Fizz path). "
            "Fallback client returned scaffold/placeholder."
            if placeholder
            else None
        ),
    }
