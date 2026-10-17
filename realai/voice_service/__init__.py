"""Shared local voice service: ONE client the hive, agents, CLI and UI call for TTS/ASR.

Recommendation (decision 4): the Voice Lab / voice trainer (realai/voice: lab_server.py, src/, scripts/, the
:8890 API and :8787 UI) stays untouched. This package lives outside realai/voice, edits none of it, and only:
  1. calls the running Voice Lab API over HTTP (``REALAI_VOICE_LAB_URL``, default http://127.0.0.1:8890) - the lab
     process owns the loaded Kokoro/XTTS weights, so nothing is loaded twice and the trainer is never disturbed;
  2. when the lab is not running (and REALAI_VOICE_MODE is auto|engine), imports the canonical engine
     ``realai.voice.provider`` / ``realai.voice.tts_engine`` read-only, in-process (Kokoro/XTTS local or HTTP,
     Fish, Windows SAPI, Piper fallback chain; silent stub WAVs rejected via ``_is_real_wav``).
It never starts/stops the lab or trainer. An optional HTTP front-end (``python -m realai.voice_service serve``)
binds a SEPARATE port (default 127.0.0.1:8891) - it is not started automatically.

Env: REALAI_VOICE_LAB_URL, REALAI_VOICE_MODE (auto|lab|engine, default auto), REALAI_VOICE_OUT (wav output dir,
default <REALAI_HOME>/voice_out), REALAI_VOICE_SERVICE_PORT (default 8891).
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_LAB_URL = "http://127.0.0.1:8890"
DEFAULT_PORT = 8891
MIN_REAL_WAV = 64


def _is_real_wav(audio: Optional[bytes]) -> bool:
    try:
        from realai.voice.tts_engine import _is_real_wav as canon  # canonical check (read-only import)

        return bool(canon(audio))
    except Exception:
        return bool(audio) and len(audio) > MIN_REAL_WAV and audio[:4] == b"RIFF"


class VoiceClient:
    def __init__(self, lab_url: Optional[str] = None, mode: Optional[str] = None, timeout: float = 120.0) -> None:
        self.lab_url = (lab_url or os.environ.get("REALAI_VOICE_LAB_URL") or DEFAULT_LAB_URL).rstrip("/")
        self.mode = (mode or os.environ.get("REALAI_VOICE_MODE") or "auto").strip().lower()
        self.timeout = timeout

    # ------------------------------------------------------------------ lab (HTTP, read-only use)
    def _http(self, method: str, path: str, body: Optional[Dict[str, Any]] = None, timeout: float = 3.0) -> Dict[str, Any]:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.lab_url + path, data=data, method=method,
                                     headers={"Content-Type": "application/json", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8") or "{}")

    def lab_up(self) -> bool:
        if self.mode == "engine":
            return False
        try:
            return bool(self._http("GET", "/v1/voice/health", timeout=2.0))
        except Exception:
            return False

    def health(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {"service": "realai-voice-service", "mode": self.mode, "lab_url": self.lab_url}
        try:
            out["lab"] = self._http("GET", "/v1/voice/health", timeout=2.0) if self.mode != "engine" else "skipped"
            out["lab_up"] = self.mode != "engine"
        except Exception as e:
            out["lab_up"] = False
            out["lab_error"] = type(e).__name__
        try:
            from realai.voice import tts_engine

            out["engine_backend_order"] = list(tts_engine.BACKEND_ORDER)
            out["engine_importable"] = True
        except Exception as e:
            out["engine_importable"] = False
            out["engine_error"] = f"{type(e).__name__}: {e}"[:200]
        out["route"] = "lab" if out.get("lab_up") else ("engine" if self.mode in ("auto", "engine") and
                                                         out.get("engine_importable") else "none")
        return out

    # ------------------------------------------------------------------ speak / listen
    def speak(self, text: str, *, voice: Optional[str] = None, backend: Optional[str] = None,
              out_path: Optional[str] = None, save: bool = True) -> Dict[str, Any]:
        text = (text or "").strip()
        if not text:
            return {"ok": False, "error": "text_required"}
        res: Dict[str, Any]
        if self.lab_up():
            try:
                res = self._http("POST", "/v1/audio/speech", {"input": text, "voice": voice, "backend": backend,
                                                              "response_format": "json"}, timeout=self.timeout)
                res["route"] = "lab"
            except Exception as e:
                res = {"ok": False, "route": "lab", "error": f"{type(e).__name__}: {e}"[:300]}
        elif self.mode in ("auto", "engine"):
            try:
                from realai.voice.provider import get_voice_provider

                res = get_voice_provider().speak(text, voice=voice, backend=backend, prepare=True, as_base64=True)
                res["route"] = "engine"
            except Exception as e:
                res = {"ok": False, "route": "engine", "error": f"{type(e).__name__}: {e}"[:300]}
        else:
            return {"ok": False, "route": "none", "error": "voice lab not reachable and REALAI_VOICE_MODE=lab"}
        audio = base64.b64decode(res.pop("audio_b64", "") or "") if res.get("ok") else b""
        res.pop("audio", None)
        if res.get("ok") and not _is_real_wav(audio):
            res.update(ok=False, error=res.get("error") or "silent_or_invalid_wav")
        if res.get("ok") and save:
            out = Path(out_path) if out_path else _out_dir() / f"speech-{int(time.time() * 1000)}.wav"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(audio)
            res["path"] = str(out)
        res["bytes"] = len(audio)
        if not save:
            res["audio_b64"] = base64.b64encode(audio).decode("ascii")
        return res

    def transcribe(self, audio: bytes) -> Dict[str, Any]:
        if self.lab_up():
            try:
                return {**self._http("POST", "/v1/audio/transcriptions",
                                     {"audio_b64": base64.b64encode(audio).decode("ascii")}, timeout=self.timeout),
                        "route": "lab"}
            except Exception as e:
                return {"ok": False, "route": "lab", "error": f"{type(e).__name__}: {e}"[:300]}
        if self.mode in ("auto", "engine"):
            from realai.voice.provider import get_voice_provider

            return {**get_voice_provider().listen(audio), "route": "engine"}
        return {"ok": False, "route": "none", "error": "voice lab not reachable"}


def _out_dir() -> Path:
    env = os.environ.get("REALAI_VOICE_OUT")
    if env:
        return Path(env)
    home = os.environ.get("REALAI_HOME")
    return (Path(home) if home else Path.cwd()) / "voice_out"


_CLIENT: Optional[VoiceClient] = None


def get_voice_client() -> VoiceClient:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = VoiceClient()
    return _CLIENT


def speak(text: str, **kw: Any) -> Dict[str, Any]:
    return get_voice_client().speak(text, **kw)


def health() -> Dict[str, Any]:
    return get_voice_client().health()


__all__ = ["VoiceClient", "get_voice_client", "speak", "health", "DEFAULT_PORT", "DEFAULT_LAB_URL"]
