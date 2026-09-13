"""Overseer-77 persona — Hive chat with Atomic Fizz lore prompt (from overseer-bot-ai)."""

from __future__ import annotations

import json
import urllib.request
from typing import Any

ABILITY = {
    "id": "overseer",
    "name": "overseer",
    "type": "ability",
    "status": "LIVE",
    "source": "realai.atomic_fizz.overseer_prompt + overseer-bot-ai persona",
    "dest": "abilities/overseer.py",
    "capabilities": ["overseer", "vault77", "wasteland_persona"],
    "secrets_policy": "none — prompt only; no Twitter/wallet keys from overseer-bot-ai",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    from realai.atomic_fizz.overseer_prompt import OVERSEER_SYSTEM_PROMPT, build_overseer_messages

    ctx = dict(context or {})
    ctx.update(kwargs)
    action = str(ctx.get("action") or "chat").lower().strip()
    text = str(ctx.get("text") or ctx.get("prompt") or input or "").strip()

    if action in {"prompt", "system", "persona"}:
        return {
            "ok": True,
            "ability": "overseer",
            "action": "prompt",
            "system_prompt": OVERSEER_SYSTEM_PROMPT,
            "source": "overseer-bot-ai (persona extract)",
        }

    if not text:
        return {"ok": False, "error": "text_required", "ability": "overseer", "hint": "Pass input/text to chat as Overseer-77"}

    messages = build_overseer_messages(text, context=str(ctx.get("lore_context") or ctx.get("context") or ""))
    try:
        body = json.dumps(
            {
                "model": ctx.get("model") or "realai-default-coder",
                "messages": messages,
                "max_tokens": int(ctx.get("max_tokens") or 180),
                "temperature": float(ctx.get("temperature") or 0.85),
            }
        ).encode()
        req = urllib.request.Request(
            "http://127.0.0.1:8001/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        reply = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        return {
            "ok": True,
            "ability": "overseer",
            "action": "chat",
            "reply": reply,
            "persona": "OVERSEER-77",
        }
    except Exception as e:
        return {
            "ok": True,
            "ability": "overseer",
            "action": "chat",
            "reply": None,
            "fallback": f"[Overseer offline echo] {text}",
            "error": str(e),
            "system_prompt_available": True,
        }
