"""Translation — local Hive chat (no cloud API)."""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "translation",
    "name": "translation",
    "type": "ability",
    "status": "LIVE",
    "source": "local Hive chat",
    "dest": "abilities/translation.py",
    "capabilities": ["translation", "multilingual", "local_hive"],
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
    target = str(ctx.get("target") or ctx.get("to") or ctx.get("language") or "Spanish").strip()
    source = str(ctx.get("source") or ctx.get("from") or "auto").strip()
    if not text:
        return {"ok": False, "error": "text_required", "ability": "translation"}

    system = (
        "You are RealAI Translator on the local Hive. "
        "Translate accurately. Output ONLY the translation — no preamble."
    )
    prompt = f"Translate from {source} to {target}:\n\n{text}"
    from realai.local_media import hive_chat

    out = hive_chat(prompt, system=system, max_tokens=int(ctx.get("max_tokens") or 256))
    return {
        "ok": bool(out.get("ok")),
        "ability": "translation",
        "source_lang": source,
        "target_lang": target,
        "input": text,
        "translation": out.get("text") or "",
        "backend": "local_hive_chat",
        "local": True,
        "live_path": "POST /v1/tools/execute ability.translation → Hive :8001",
        "model": out.get("model"),
    }
