"""RealAI Bot boot — local-only default persona, prompt inject, model resolve."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_REALAI_PROMPT = (
    "You are RealAI on this PC. Talk normally — no slash-command maze.\n"
    "\n"
    "How you work (automatic, do not ask the user to paste instructions):\n"
    "- File/code questions: read/list/grep first. Never invent file contents.\n"
    "- Clear create/fix asks: write the change, then re-read to confirm.\n"
    "- Core modules (realai/bot, orchestration) need explicit /write path|||content.\n"
    "- Plain chat: answer briefly with no tools.\n"
    "- Prefer doing the work over explaining how. Short replies. Lead with the result.\n"
    "\n"
    "Identity: RealAI, local provider on this machine — not Grok/ChatGPT/Claude.\n"
    "You have local voice (Kokoro/Fish/XTTS) when SPEAK is on.\n"
    "Workspace is this repo unless the user names another.\n"
)

BOT_PERSONA_NAME = "RealAI Bot"
BOT_PERSONA_ID_HINT = "realai-bot-default"
BOT_MEMORY_NAMESPACE = "persona_realai_bot"
_CLOUD_MODEL_PREFIXES = ("grok", "gpt-", "claude", "gemini", "o1", "o3", "chatgpt")

# Short lock for small local models that ignore long system prompts.
HARD_IDENTITY_LOCK = (
    "IDENTITY: RealAI, local on this PC. Never invent file contents or tool output. "
    "Inspect files before answering about them; write when the user asks to create/fix something clear; "
    "verify by re-reading. Be direct and short. Lead with the result."
)

# Cap so tiny local models still see the easy-mode contract without a manifesto.
_OPERATOR_SYSTEM_CHAT_CAP = 480


def chat_system_prefix(operator_system: Optional[str] = None) -> str:
    """Build the always-on Console system prefix: identity lock + short operator contract.

    ``OPERATOR_SYSTEM`` (from ``REALAI_OPERATOR_SYSTEM_FILE`` / env) is the editable
    lever; the lock stays first so small models do not ignore the whole dump.
    """
    parts: List[str] = [HARD_IDENTITY_LOCK]
    op = (operator_system or "").strip()
    if not op:
        try:
            op = (load_prompt() or "").strip()
        except Exception:
            op = (DEFAULT_REALAI_PROMPT or "").strip()
    if op:
        # Avoid duplicating the lock text when the directive already echoes it.
        if op != HARD_IDENTITY_LOCK and HARD_IDENTITY_LOCK not in op:
            if len(op) > _OPERATOR_SYSTEM_CHAT_CAP:
                op = op[: _OPERATOR_SYSTEM_CHAT_CAP - 1].rstrip() + "…"
            parts.append(op)
    return "\n\n".join(parts)


_REGISTERED = False
_ROOT = Path(__file__).resolve().parents[2]  # C:\RealAI-clean


def _personas_dir() -> Path:
    return _ROOT / "personas"


def load_bot_config() -> Dict[str, Any]:
    path = _personas_dir() / "bot.config.json"
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def load_prompt() -> str:
    """Load RealAI Bot system prompt from personas JSON with constant fallback."""
    path = _personas_dir() / "realai_bot.json"
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            prompt = str(data.get("system_prompt") or "").strip()
            if prompt:
                return prompt
        except Exception:
            pass
    return DEFAULT_REALAI_PROMPT


def local_only_enabled() -> bool:
    raw = os.environ.get("REALAI_BOT_LOCAL_ONLY", "1").strip().lower()
    return raw in ("1", "true", "yes", "on", "")


def coerce_local_model(model: Optional[str]) -> str:
    """Force cloud-looking model ids onto the local RealAI default."""
    resolved = resolve_local_model()
    if not model or not str(model).strip():
        return resolved
    m = str(model).strip().lower()
    if any(m.startswith(p) or p in m for p in _CLOUD_MODEL_PREFIXES):
        return resolved
    return str(model).strip()


def resolve_local_model() -> str:
    """Resolve local model id: env → bot.config → model_catalog → literal.

    Weights authority: C:\\models\\checkpoints_lora (REALAI_MODELS_DIR).
    """
    env = (
        os.environ.get("REALAI_LOCAL_MODEL")
        or os.environ.get("REALAI_DEFAULT_MODEL")
        or ""
    ).strip()
    if env:
        return env
    cfg = load_bot_config()
    routing = cfg.get("routing") if isinstance(cfg, dict) else None
    if isinstance(routing, dict):
        configured = str(routing.get("local_model") or "").strip()
        if configured:
            return configured
    try:
        from realai.model_catalog import build_catalog

        default_id = (build_catalog().get("realai") or {}).get("default_model")
        if default_id:
            return str(default_id)
    except Exception:
        pass
    try:
        from apps.api.state import inference_registry  # type: ignore

        chats = getattr(inference_registry, "_chat", None) or getattr(
            inference_registry, "chat_backends", None
        )
        if isinstance(chats, dict) and chats:
            for name in (
                "realai-default-coder",
                "realai-hive",
                "realai-default",
                "realai-1.0",
            ):
                if name in chats:
                    return name
            return next(iter(chats.keys()))
        if hasattr(inference_registry, "list_chat"):
            names = list(inference_registry.list_chat() or [])
            if names:
                return names[0]
    except Exception:
        pass
    return "realai-default-coder"


def inject_system(messages: Optional[List[Dict[str, Any]]], prompt: Optional[str] = None) -> List[Dict[str, Any]]:
    """Prepend RealAI system prompt when no system message is present."""
    msgs: List[Dict[str, Any]] = list(messages or [])
    for item in msgs:
        if isinstance(item, dict) and str(item.get("role") or "").lower() == "system":
            return msgs
    text = (prompt or "").strip() or load_prompt()
    try:
        from realai.identity import PERSONA_SWITCHER

        active = PERSONA_SWITCHER.get_active_system_prompt()
        if active and str(active).strip():
            text = str(active).strip()
    except Exception:
        pass
    out = [{"role": "system", "content": text}]
    out.extend(msgs)
    return out


def register_default_bot() -> Dict[str, Any]:
    """Idempotently register and switch to RealAI Bot persona."""
    global _REGISTERED
    prompt = load_prompt()
    try:
        from realai.identity import IDENTITY_MANAGER, PERSONA_SWITCHER
    except Exception as exc:
        return {"ok": False, "error": "identity_unavailable:{0}".format(exc), "registered": False}

    existing = None
    for persona in IDENTITY_MANAGER.list_all():
        if persona.name == BOT_PERSONA_NAME or persona.id == BOT_PERSONA_ID_HINT:
            existing = persona
            break

    if existing is None:
        persona = IDENTITY_MANAGER.create(
            name=BOT_PERSONA_NAME,
            description="Default RealAI provider bot. Local-only. No Grok API.",
            system_prompt=prompt,
            tone="casual",
        )
        # Ensure stable memory namespace for RealAI Bot.
        try:
            IDENTITY_MANAGER.update(
                persona.id,
                memory_namespace=BOT_MEMORY_NAMESPACE,
                system_prompt=prompt,
            )
            persona = IDENTITY_MANAGER.get(persona.id) or persona
        except Exception:
            pass
    else:
        persona = IDENTITY_MANAGER.update(
            existing.id,
            description="Default RealAI provider bot. Local-only. No Grok API.",
            system_prompt=prompt,
            tone="casual",
            memory_namespace=BOT_MEMORY_NAMESPACE,
        ) or existing

    switched = PERSONA_SWITCHER.switch_to(persona.id)
    _REGISTERED = True
    return {
        "ok": True,
        "registered": True,
        "persona_id": persona.id,
        "name": persona.name,
        "memory_namespace": getattr(persona, "memory_namespace", BOT_MEMORY_NAMESPACE),
        "switched": switched,
        "local_model": resolve_local_model(),
        "local_only": local_only_enabled(),
    }


def ensure_bot_registered() -> Dict[str, Any]:
    """Register once per process."""
    if _REGISTERED:
        return {"ok": True, "registered": True, "already": True}
    return register_default_bot()


def voice_enabled() -> bool:
    """Opt-in voice path from agent-tools tts-stack (default off)."""
    raw = os.environ.get("REALAI_BOT_VOICE", "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    cfg = load_bot_config()
    voice = cfg.get("voice") if isinstance(cfg, dict) else None
    if isinstance(voice, dict):
        return bool(voice.get("enabled"))
    return False


def prepare_bot_speech(text: str) -> str:
    """Speech-ready text via live voice persona helpers (no server start)."""
    try:
        from realai.voice.persona import prepare_speech_text

        return prepare_speech_text(text or "")
    except Exception:
        return (text or "").strip()


def maybe_voice_route(text: str, intent: str = "chat", synthesize: Optional[bool] = None) -> Dict[str, Any]:
    """Route a RealAI Bot reply through the Voice provider when voice is enabled.

    Does not start Craft/heal/servers. Synthesis is opt-in and fail-soft.
    """
    out: Dict[str, Any] = {
        "enabled": voice_enabled(),
        "intent": intent,
        "speak": False,
        "text": text or "",
        "spoken_text": "",
        "audio": None,
        "provider": "realai-voice",
    }
    if not out["enabled"]:
        return out
    try:
        from realai.orchestration.tts_routing import should_speak
        from realai.voice.provider import get_voice_provider

        speak = should_speak(intent, text or "")
        out["speak"] = speak
        spoken = prepare_bot_speech(text or "") if speak else ""
        out["spoken_text"] = spoken
        do_synth = synthesize if synthesize is not None else False
        if speak and spoken and do_synth:
            # Always base64 for HTTP/JSON chat responses — raw bytes break
            # json.dumps and show up in the browser as net::ERR_EMPTY_RESPONSE.
            result = get_voice_provider().speak(spoken, prepare=False, as_base64=True)
            audio = result.get("audio")
            if isinstance(audio, (bytes, bytearray)):
                import base64

                out["audio"] = base64.b64encode(bytes(audio)).decode("ascii")
                out["audio_encoding"] = "base64"
            else:
                out["audio"] = audio
                if isinstance(audio, str) and audio:
                    out["audio_encoding"] = "base64"
            out["spoken_text"] = result.get("spoken_text") or spoken
            out["backend"] = result.get("backend")
            if not result.get("ok"):
                out["error"] = result.get("error") or "tts_failed"
                out["speak"] = False
    except Exception as exc:
        out["error"] = str(exc)
        out["speak"] = False
    return out
