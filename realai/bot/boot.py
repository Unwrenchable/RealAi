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

# Cap the editable directive body so tiny local models still see the contract.
# The reply contract itself is prepended and is not truncated away.
_OPERATOR_SYSTEM_CHAT_CAP = 480
# Sticky facts sit beside the directive, not inside its 480-char clip.
_OPERATOR_MEMORY_CHAT_CAP = 900


def operator_directive_path() -> Optional[Path]:
    """On-disk Console operator directive. Non-optional for Natural Mode.

    ``REALAI_OPERATOR_SYSTEM_FILE`` wins when it points at a real file.
    Otherwise the product ``docs/CONSOLE_OPERATOR_DIRECTIVE.md`` is used.
    """
    env = (os.environ.get("REALAI_OPERATOR_SYSTEM_FILE") or "").strip()
    if env:
        p = Path(env)
        if p.is_file():
            return p
    cand = _ROOT / "docs" / "CONSOLE_OPERATOR_DIRECTIVE.md"
    if cand.is_file():
        return cand
    return None


def load_operator_directive() -> str:
    """Load the operator directive. Empty only when the file and env are both missing."""
    path = operator_directive_path()
    if path is not None:
        try:
            text = path.read_text(encoding="utf-8").strip()
            if text:
                return text
        except Exception:
            pass
    return (os.environ.get("REALAI_OPERATOR_SYSTEM") or "").strip()


def _clip_prompt(text: str, limit: int) -> str:
    raw = (text or "").strip()
    if len(raw) <= limit:
        return raw
    return raw[: limit - 1].rstrip() + "…"


def chat_system_prefix(
    operator_system: Optional[str] = None,
    user_text: Optional[str] = None,
    *,
    hat: Optional[str] = None,
) -> str:
    """Build the always-on Console system prefix: identity lock + directive + reply contract.

    The directive file is loaded even when the caller passes only the default
    bot prompt or an empty string. ``NATURAL_REPLY_CONTRACT`` stays in front of
    the capped directive body. Sticky operator memory is appended after that
    clip so a long directive cannot drop the facts.

    When ``hat`` or ``user_text`` is set, a one-turn Mode Active block is
    appended (inferred from the prompt when ``hat`` is omitted). Empty calls
    stay hat-free so a prefix with no prompt does not invent a turn.
    """
    parts: List[str] = [HARD_IDENTITY_LOCK]
    try:
        from realai.bot.natural_mode import NATURAL_REPLY_CONTRACT
    except Exception:
        NATURAL_REPLY_CONTRACT = (
            "REPLY CONTRACT: Summary / What changed / Verify / Next. "
            "MAX_TOOLS_THIS_TURN=3. Chat abort 180s. "
            "Never say LANDED unless a write tool succeeded."
        )
    op = (operator_system or "").strip()
    directive = load_operator_directive()
    chunks: List[str] = [NATURAL_REPLY_CONTRACT]
    if directive and directive not in op:
        chunks.append(_clip_prompt(directive, _OPERATOR_SYSTEM_CHAT_CAP))
    elif directive and directive == op:
        chunks.append(_clip_prompt(directive, _OPERATOR_SYSTEM_CHAT_CAP))
    if op and op != directive and HARD_IDENTITY_LOCK not in op and NATURAL_REPLY_CONTRACT not in op:
        chunks.append(_clip_prompt(op, _OPERATOR_SYSTEM_CHAT_CAP))
    if len(chunks) == 1 and not directive:
        try:
            fallback = (load_prompt() or "").strip()
        except Exception:
            fallback = (DEFAULT_REALAI_PROMPT or "").strip()
        if fallback and fallback != HARD_IDENTITY_LOCK:
            chunks.append(_clip_prompt(fallback, _OPERATOR_SYSTEM_CHAT_CAP))
    blob = "\n\n".join(c for c in chunks if c)
    if blob and blob != HARD_IDENTITY_LOCK and HARD_IDENTITY_LOCK not in blob:
        parts.append(blob)
    try:
        memory = load_operator_memory()
    except Exception:
        memory = ""
    if memory and memory not in "\n".join(parts):
        parts.append(memory)
    try:
        from realai.bot.hat_routing import hat_turn_prefix, infer_hat, normalize_hat

        resolved = ""
        if hat:
            resolved = normalize_hat(hat)
        elif (user_text or "").strip():
            resolved = infer_hat(user_text)
        if resolved:
            note = hat_turn_prefix(resolved)
            if note and note not in "\n".join(parts):
                parts.append(note)
    except Exception:
        pass
    return "\n\n".join(parts)


_REGISTERED = False
_ROOT = Path(__file__).resolve().parents[2]  # C:\RealAI-clean


def operator_memory_path() -> Optional[Path]:
    """On-disk sticky operator facts. Missing file is non-fatal.

    ``REALAI_OPERATOR_MEMORY_FILE`` wins when it points at a real file.
    Otherwise the product ``docs/OPERATOR_MEMORY.md`` is used.
    An explicit path that is missing does not raise; the product file is
    the fallback, and a missing product file yields no path.
    """
    env = (os.environ.get("REALAI_OPERATOR_MEMORY_FILE") or "").strip()
    if env:
        p = Path(env)
        if p.is_file():
            return p
    cand = _ROOT / "docs" / "OPERATOR_MEMORY.md"
    if cand.is_file():
        return cand
    return None


def load_operator_memory() -> str:
    """Load sticky operator memory for the Console system prefix.

    Returns ``""`` when the file is missing, empty, or unreadable.
    """
    try:
        path = operator_memory_path()
        if path is None or not path.is_file():
            return ""
        text = path.read_text(encoding="utf-8").strip()
    except Exception:
        return ""
    if not text:
        return ""
    return _clip_prompt(text, _OPERATOR_MEMORY_CHAT_CAP)


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
