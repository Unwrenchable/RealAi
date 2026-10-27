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
        if action in {"status", "info", ""}:
            return {
                "ok": True,
                "ability": "overseer",
                "action": "status",
                "persona": "Overseer-77",
                "hint": "Pass input/text to chat as Overseer-77",
                "system_prompt_preview": OVERSEER_SYSTEM_PROMPT[:240] + "…",
            }
        text = "Citizen, report vault status."

    messages = build_overseer_messages(text, context=str(ctx.get("lore_context") or ctx.get("context") or ""))
    try:
        from realai.local_media import local_chat

        out = local_chat(
            messages,
            max_tokens=int(ctx.get("max_tokens") or 180),
            temperature=float(ctx.get("temperature") or 0.85),
        )
        if not out.get("ok"):
            raise ConnectionError(out.get("error") or "no local chat endpoint reachable")
        reply = out.get("text") or ""
        return {
            "ok": True,
            "ability": "overseer",
            "action": "chat",
            "reply": reply,
            "persona": "OVERSEER-77",
            "endpoint": out.get("endpoint"),
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
