"""Shared voice service (decision 4): lab-first HTTP client, engine fallback, trainer untouched."""
from __future__ import annotations

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

WAV = b"RIFF" + b"\x00" * 600


class _Lab(BaseHTTPRequestHandler):
    seen = []

    def _send(self, obj):
        raw = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        self._send({"ok": True, "provider": "fake-lab"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        _Lab.seen.append((self.path, body))
        self._send({"ok": True, "backend": "xtts", "audio_b64": base64.b64encode(WAV).decode()})

    def log_message(self, *a):
        pass


def test_speak_via_running_lab(tmp_path):
    from realai.voice_service import VoiceClient

    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Lab)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        c = VoiceClient(lab_url=f"http://127.0.0.1:{srv.server_port}", mode="auto")
        assert c.health()["route"] == "lab"
        r = c.speak("hello travis", voice="laura", out_path=str(tmp_path / "x.wav"))
        assert r["ok"] and r["route"] == "lab" and Path(r["path"]).read_bytes() == WAV
        assert _Lab.seen[-1][0] == "/v1/audio/speech" and _Lab.seen[-1][1]["response_format"] == "json"
    finally:
        srv.shutdown()


def test_lab_only_mode_without_lab_does_not_fall_back():
    from realai.voice_service import VoiceClient

    r = VoiceClient(lab_url="http://127.0.0.1:9", mode="lab").speak("hi")
    assert r["ok"] is False and r["route"] == "none"


def test_engine_fallback_rejects_silent_wav(monkeypatch):
    from realai.voice import provider
    from realai.voice_service import VoiceClient

    class P:
        def speak(self, *a, **k):
            return {"ok": True, "backend": "piper", "audio_b64": base64.b64encode(b"RIFF" + b"\x00" * 40).decode()}

    monkeypatch.setattr(provider, "get_voice_provider", lambda: P())
    r = VoiceClient(lab_url="http://127.0.0.1:9", mode="auto").speak("hi", save=False)
    assert r["route"] == "engine" and r["ok"] is False


def test_serve_refuses_lab_and_live_ports():
    from realai.voice_service.__main__ import main

    for port in (8890, 8787, 8000, 8001, 8080):
        assert main(["serve", "--port", str(port)]) == 2


def test_agent_tools_tts_engine_is_canonical_shim_and_lab_untouched():
    import agent_tools.tts_engine as shim
    from realai.voice import tts_engine

    assert shim.TTSEngine is tts_engine.TTSEngine and shim._is_real_wav is tts_engine._is_real_wav
    src = Path(tts_engine.__file__).read_text(encoding="utf-8")
    for name in ("_apply_provider_config", "_maybe_clip_speaker_wav", "_patch_torchaudio_load_soundfile", "WindowsSAPI",
                 "def _synthesize_local", "def _ensure_local", "def _synthesize_http", "MIN_REAL_WAV"):
        assert name in src
    assert "voice_service" not in src  # the lab/engine does not depend on the new client
