"""Supportive counseling drafts — local Hive (not clinical care; no cloud API)."""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "therapy_counseling",
    "name": "therapy_counseling",
    "type": "ability",
    "status": "LIVE",
    "source": "local Hive chat",
    "dest": "abilities/therapy_counseling.py",
    "capabilities": ["counseling", "support", "local_hive"],
    "secrets_policy": "none",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    ctx = dict(context or {})
    ctx.update(kwargs)
    text = str(ctx.get("text") or ctx.get("input") or input or "").strip()
    if not text:
        return {"ok": False, "error": "text_required", "ability": "therapy_counseling"}

    system = (
        "You are RealAI Supportive Counselor on the local Hive. "
        "You are NOT a licensed clinician and do not diagnose. "
        "Respond with empathy, reflective listening, and practical coping suggestions. "
        "If crisis/self-harm is mentioned, urge contacting local emergency services / hotlines. "
        "Keep replies grounded and brief."
    )
    from realai.local_media import hive_chat

    out = hive_chat(text, system=system, max_tokens=int(ctx.get("max_tokens") or 384))
    return {
        "ok": bool(out.get("ok")),
        "ability": "therapy_counseling",
        "input": text,
        "reply": out.get("text") or "",
        "disclaimer": "Not clinical therapy — local supportive draft only.",
        "backend": "local_hive_chat",
        "local": True,
        "live_path": "POST /v1/tools/execute ability.therapy_counseling → Hive :8001",
        "model": out.get("model"),
    }
