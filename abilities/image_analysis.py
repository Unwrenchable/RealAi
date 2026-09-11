"""Image analysis — local Pillow vision first; optional xAI vision if keyed."""

from __future__ import annotations

from pathlib import Path
from typing import Any

ABILITY = {
    "id": "image_analysis",
    "name": "image_analysis",
    "type": "ability",
    "status": "LIVE",
    "source": "realai.local_media (+ optional xai_media)",
    "dest": "abilities/image_analysis.py",
    "capabilities": ["vision", "image_analysis", "local_pillow"],
    "secrets_policy": "none required",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    image_url = str(ctx.get("image_url") or ctx.get("url") or ctx.get("path") or input or "").strip()
    action = str(ctx.get("action") or "analyze").lower()
    prompt = str(
        ctx.get("prompt")
        or "Describe this image in detail. List notable objects, style, and any text."
    )
    if not image_url:
        return {"ok": False, "error": "image_url_or_path_required", "ability": "image_analysis"}

    prefer_cloud = str(ctx.get("backend") or "").lower() in {"xai", "grok", "cloud"}
    if prefer_cloud:
        try:
            from realai.providers import xai_media

            if xai_media.has_api_key():
                result = xai_media.analyze_image(image_url, prompt=prompt, model=ctx.get("model"))
                return {
                    "ok": True,
                    "ability": "image_analysis",
                    "action": action,
                    "image_url": image_url,
                    "result": result,
                    "placeholder": False,
                    "source": "xai_vision",
                    "local": False,
                }
        except Exception:
            pass

    from realai.local_media import analyze_image_local

    # Prefer a local file if a generated asset path was passed
    ref = image_url
    if not Path(ref).is_file() and not ref.startswith(("http://", "https://", "data:")):
        # Try scan_results/local_media for bare filenames
        cand = Path(__file__).resolve().parents[1] / "scan_results" / "local_media" / Path(ref).name
        if cand.is_file():
            ref = str(cand)

    local = analyze_image_local(ref)
    return {
        "ok": bool(local.get("ok")),
        "ability": "image_analysis",
        "action": action,
        "image_url": image_url,
        "result": local,
        "placeholder": False if local.get("ok") else True,
        "source": "local_pillow",
        "local": True,
        "live_path": "POST /v1/tools/execute ability.image_analysis (local Pillow)",
        "error": local.get("error"),
    }
