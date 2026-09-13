"""Image generation — Atomic Fizz xAI Imagine client (+ desktop lambda inventory)."""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "image_generation",
    "name": "image_generation",
    "type": "ability",
    "status": "PARTIAL",
    "source": "realai.providers.xai_media + Atomic Fizz backend/lib/grok.js",
    "dest": "abilities/image_generation.py",
    "capabilities": ["image", "images/generations", "grok-imagine"],
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
        return {"ok": False, "error": "prompt_required", "ability": "image_generation"}

    from realai.providers import xai_media

    st = xai_media.status()
    if not st.get("api_key_configured"):
        # Still expose desktop lambda inventory for offline honesty
        try:
            from abilities.desktop_lambda_image import run as lambda_run

            wrapped = lambda_run(input=prompt, context={**ctx, "prompt": prompt})
        except Exception as e:
            wrapped = {"ok": False, "error": str(e)}
        return {
            "ok": False,
            "ability": "image_generation",
            "error": "xai_api_key_missing",
            "hint": "Set XAI_API_KEY (or GROK_API_KEY) to call api.x.ai /v1/images/generations",
            "source": "ATOMIC-FIZZ backend/lib/grok.js → realai.providers.xai_media",
            "delegate_inventory": wrapped,
            "status": st,
        }

    try:
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
        }
    except Exception as e:
        return {"ok": False, "ability": "image_generation", "error": str(e), "prompt": prompt}
