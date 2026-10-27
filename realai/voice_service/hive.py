"""Orchestrator-facing voice tools (voice_health / voice_inventory / voice_speak / voice_listen).

Same names and argument shapes as ``realai.voice.hive_tools`` (whose TOOLS schema the orchestrator still
advertises), but every call goes through the shared ``realai.voice_service`` client: Voice Lab HTTP API on
:8890 when it is up, in-process engine otherwise. Never starts/stops the lab or the voice trainer.
"""
from __future__ import annotations

import base64
from typing import Any, Callable, Dict, Optional

from realai.voice_service import get_voice_client


def _compact(res: Dict[str, Any]) -> Dict[str, Any]:
    b64 = res.get("audio_b64") or ""
    if len(b64) > 240:
        res["audio_b64_preview"] = b64[:120] + "…"
        res["audio_b64_len"] = len(b64)
    return res


def voice_speak(text: str = "", voice: Optional[str] = None, backend: Optional[str] = None, **kw: Any) -> Dict[str, Any]:
    text = str(text or kw.get("input") or kw.get("prompt") or "").strip() or "RealAI voice smoke check."
    return _compact(get_voice_client().speak(text, voice=voice, backend=backend, save=False))


def voice_inventory(**_: Any) -> Dict[str, Any]:
    return get_voice_client().inventory()


def voice_health(**_: Any) -> Dict[str, Any]:
    return get_voice_client().health()


def voice_listen(audio_b64: str = "", **kw: Any) -> Dict[str, Any]:
    client = get_voice_client()
    demo = str(kw.get("demo_text") or "").strip()
    if not audio_b64 and demo:  # TTS -> ASR roundtrip for smoke without mic/file
        spoken = client.speak(demo, save=False)
        audio_b64 = str(spoken.get("audio_b64") or "")
        if not audio_b64:
            return {"ok": False, "error": "demo_tts_failed", "tts": {k: v for k, v in spoken.items() if k != "audio_b64"}}
    try:
        audio = base64.b64decode(audio_b64) if audio_b64 else b""
    except Exception as exc:
        return {"ok": False, "error": f"bad_base64: {exc}"}
    if not audio:
        return {"ok": False, "error": "audio_required", "hint": "Pass audio_b64 or demo_text for TTS->ASR roundtrip"}
    try:
        res = client.transcribe(audio)
    except Exception as exc:
        res = {"ok": False, "error": f"{type(exc).__name__}: {exc}"[:300]}
    if res.get("ok") and res.get("text"):
        return res
    try:  # same last resort as before: vosk ability
        from abilities.audio_transcription import run as asr_run

        out = asr_run(context={"audio_b64": audio_b64})
        if out.get("ok") and out.get("text"):
            return {"ok": True, "text": out.get("text"), "backend": out.get("backend"), "ability": "audio_transcription",
                    "route": "ability", "voice_service_error": res.get("error")}
    except Exception:
        pass
    return res


DISPATCH: Dict[str, Callable[..., Dict[str, Any]]] = {
    "voice_speak": voice_speak, "voice_inventory": voice_inventory,
    "voice_health": voice_health, "voice_listen": voice_listen,
}


def execute(name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    fn = DISPATCH.get(name)
    if not fn:
        return {"ok": False, "error": f"unknown_voice_tool: {name}"}
    return fn(**(arguments or {}))
