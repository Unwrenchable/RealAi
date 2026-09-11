"""RealAI Voice Engine.

Picks a TTS backend (Kokoro, Fish Speech, XTTS, Windows SAPI, Piper) and turns
speech-ready text into WAV bytes. Import is side-effect free.
Does not start servers, Craft, or llama.

Silent Piper stubs (44-byte empty WAV) are rejected so fallback continues.
On Windows, System.Speech (SAPI) is the reliable local fallback when Kokoro
HTTP is not running.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from .tts_base import TTSBackend
from .tts_piper import PiperTTS
from .persona import DEFAULT_PERSONA, prepare_speech_text

# Prefer neural engines when up; Windows SAPI always works locally.
# Default preference is overridden by REALAI_TTS_BACKEND / provider_config.json.
BACKEND_ORDER = ("xtts", "kokoro", "fish", "windows_sapi", "piper")
MIN_REAL_WAV = 64


def _apply_provider_config() -> None:
    """Load realai/voice/provider_config.json into env if present."""
    try:
        cfg_path = Path(__file__).resolve().parent / "provider_config.json"
        if not cfg_path.is_file():
            return
        import json

        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        tts = cfg.get("tts") if isinstance(cfg, dict) else None
        if not isinstance(tts, dict):
            return
        eng = str(tts.get("engine") or "").strip().lower()
        if eng and not os.environ.get("REALAI_TTS_BACKEND"):
            os.environ["REALAI_TTS_BACKEND"] = eng
        speaker = str(tts.get("speaker_wav") or "").strip()
        if speaker and not os.environ.get("REALAI_XTTS_SPEAKER"):
            os.environ["REALAI_XTTS_SPEAKER"] = speaker
        model = str(tts.get("model_path") or "").strip()
        if model:
            mp = Path(model)
            if mp.parent.is_dir() and not os.environ.get("REALAI_XTTS_MODEL_DIR"):
                os.environ["REALAI_XTTS_MODEL_DIR"] = str(mp.parent)
    except Exception:
        pass


def _is_real_wav(audio: Optional[bytes]) -> bool:
    if not audio or len(audio) < MIN_REAL_WAV:
        return False
    return audio[:4] == b"RIFF" or len(audio) > 512


class KokoroTTS:
    """Kokoro TTS — HTTP server when up, else in-process from local weights.

    Local weights: C:\\models\\checkpoints_lora\\Kokoro (REALAI_KOKORO_MODEL_DIR).
    Prefer :8880 if running; otherwise load kokoro-v1_0.pth + voices/*.pt in-process
    so Hive does not fall through to Windows SAPI when models are on disk.
    """

    name = "kokoro"
    _local_pipeline = None
    _local_model = None
    _local_error: Optional[str] = None

    def __init__(self, base_url: Optional[str] = None) -> None:
        from realai.voice.paths import KOKORO_DIR, kokoro_checkpoint, kokoro_voices_dir

        self.model_dir = KOKORO_DIR
        self.checkpoint = kokoro_checkpoint()
        self.voices_dir = kokoro_voices_dir()
        self.base_url = (
            base_url
            or os.environ.get("REALAI_KOKORO_URL")
            or "http://127.0.0.1:8880"
        ).rstrip("/")

    def _synthesize_http(self, text: str, voice: str) -> bytes:
        import json
        import urllib.request

        voice_path = ""
        try:
            cand = self.voices_dir / f"{voice}.pt"
            if cand.is_file():
                voice_path = str(cand)
        except Exception:
            pass
        payload_obj = {
            "model": "kokoro",
            "input": text,
            "voice": voice,
            "response_format": "wav",
        }
        if voice_path:
            payload_obj["voice_path"] = voice_path
        if self.checkpoint is not None:
            payload_obj["model_path"] = str(self.checkpoint)
        if self.model_dir.is_dir():
            payload_obj["model_dir"] = str(self.model_dir)
        payload = json.dumps(payload_obj).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/v1/audio/speech",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read()
        if not _is_real_wav(data):
            raise RuntimeError("kokoro returned empty/silent wav")
        return data

    def _ensure_local(self) -> None:
        if KokoroTTS._local_pipeline is not None:
            return
        if KokoroTTS._local_error:
            raise RuntimeError(KokoroTTS._local_error)
        if self.checkpoint is None or not self.checkpoint.is_file():
            KokoroTTS._local_error = "kokoro checkpoint missing"
            raise RuntimeError(KokoroTTS._local_error)
        try:
            import torch
            from kokoro import KModel, KPipeline
        except Exception as exc:
            KokoroTTS._local_error = f"kokoro package unavailable: {exc}"
            raise RuntimeError(KokoroTTS._local_error) from exc

        config = self.model_dir / "config.json"
        model = KModel(
            config=str(config) if config.is_file() else None,
            model=str(self.checkpoint),
        )
        # CPU is fine for short console replies; honor CUDA if present.
        if torch.cuda.is_available() and os.environ.get("REALAI_KOKORO_DEVICE", "").lower() in (
            "cuda",
            "gpu",
            "1",
            "true",
        ):
            model = model.to("cuda")
        else:
            model = model.to("cpu")
        model.eval()
        pipeline = KPipeline(lang_code=os.environ.get("REALAI_KOKORO_LANG", "a"), model=model)
        KokoroTTS._local_model = model
        KokoroTTS._local_pipeline = pipeline

    def _synthesize_local(self, text: str, voice: str) -> bytes:
        import io
        import wave

        import numpy as np
        import torch

        self._ensure_local()
        pipeline = KokoroTTS._local_pipeline
        assert pipeline is not None

        voice_arg: object = voice
        try:
            cand = self.voices_dir / f"{voice}.pt"
            if cand.is_file():
                voice_arg = torch.load(str(cand), weights_only=True, map_location="cpu")
        except Exception:
            voice_arg = voice

        chunks = []
        for _gs, _ps, audio in pipeline(text, voice=voice_arg, speed=1.0):
            if audio is None:
                continue
            if hasattr(audio, "detach"):
                audio = audio.detach().cpu().numpy()
            arr = np.asarray(audio, dtype=np.float32).reshape(-1)
            if arr.size:
                chunks.append(arr)
        if not chunks:
            raise RuntimeError("kokoro local produced no audio")
        pcm = np.concatenate(chunks)
        pcm = np.clip(pcm, -1.0, 1.0)
        pcm16 = (pcm * 32767.0).astype(np.int16)
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes(pcm16.tobytes())
        data = buf.getvalue()
        if not _is_real_wav(data):
            raise RuntimeError("kokoro local empty/silent wav")
        return data

    def synthesize(self, text: str) -> bytes:
        voice = os.environ.get("REALAI_KOKORO_VOICE", "af_heart")
        http_err: Optional[Exception] = None
        # Fast path: dedicated Kokoro HTTP if already running.
        try:
            return self._synthesize_http(text, voice)
        except Exception as exc:
            http_err = exc
        # In-process from your on-disk weights (no :8880 required).
        try:
            return self._synthesize_local(text, voice)
        except Exception as local_err:
            raise RuntimeError(
                f"kokoro http failed ({http_err}); local failed ({local_err})"
            ) from local_err


class FishSpeechTTS:
    name = "fish"

    def __init__(self, base_url: Optional[str] = None) -> None:
        from realai.voice.paths import FISH_DIR, fish_checkpoint

        self.model_dir = FISH_DIR
        self.checkpoint = fish_checkpoint()
        self.base_url = (
            base_url
            or os.environ.get("REALAI_FISH_URL")
            or "http://127.0.0.1:8081"
        ).rstrip("/")

    def synthesize(self, text: str) -> bytes:
        import json
        import urllib.request

        payload_obj = {"text": text, "format": "wav"}
        if self.model_dir.is_dir():
            payload_obj["model_dir"] = str(self.model_dir)
        if self.checkpoint is not None:
            payload_obj["checkpoint"] = str(self.checkpoint)
        payload = json.dumps(payload_obj).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/v1/tts",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        if not _is_real_wav(data):
            raise RuntimeError("fish returned empty/silent wav")
        return data


def _maybe_clip_speaker_wav(path: str, max_secs: float = 12.0) -> str:
    """XTTS clones best from a short mono clip; long studio dumps are slow/noisy."""
    src = Path(path) if path else None
    if src is None or not src.is_file():
        return path
    clip = src.with_name(f"{src.stem}_clip.wav")
    try:
        import soundfile as sf

        info = sf.info(str(src))
        if float(info.duration or 0) <= max_secs and int(info.channels or 1) == 1:
            return str(src)
        if clip.is_file() and clip.stat().st_mtime >= src.stat().st_mtime:
            return str(clip)
        data, sr = sf.read(str(src), dtype="float32", always_2d=True)
        mono = data.mean(axis=1) if data.shape[1] > 1 else data[:, 0]
        need = int(sr * max_secs)
        if len(mono) > need:
            start = max(0, (len(mono) - need) // 3)
            mono = mono[start : start + need]
        sf.write(str(clip), mono, sr, subtype="PCM_16")
        return str(clip)
    except Exception:
        return path


def _patch_torchaudio_load_soundfile() -> None:
    """Windows/CPU torch 2.9+ routes torchaudio.load through torchcodec+FFmpeg.

    Voice Lab does not require FFmpeg for plain WAVs — soundfile is enough.
    """
    try:
        import torchaudio
    except Exception:
        return
    if getattr(torchaudio, "_realai_sf_patched", False):
        return
    try:
        import numpy as np
        import soundfile as sf
        import torch
    except Exception:
        return

    def _load(uri: Any, *args: Any, **kwargs: Any):  # noqa: ANN401
        path = str(uri)
        data, sr = sf.read(path, dtype="float32", always_2d=True)
        # soundfile: (frames, channels) → torchaudio: (channels, frames)
        tensor = torch.from_numpy(np.ascontiguousarray(data.T))
        return tensor, int(sr)

    torchaudio.load = _load  # type: ignore[method-assign]
    torchaudio._realai_sf_patched = True  # type: ignore[attr-defined]


class XTTSBackend:
    """XTTS — HTTP :8020 when up, else local coqui-tts with speaker_wav clone."""

    name = "xtts"
    _local_tts = None
    _local_error: Optional[str] = None

    def __init__(self, base_url: Optional[str] = None) -> None:
        from realai.voice.paths import XTTS_DIR, xtts_model, xtts_speaker_wav

        self.model_dir = XTTS_DIR
        self.model_path = xtts_model()
        speaker = xtts_speaker_wav()
        raw = str(speaker) if speaker is not None else (
            os.environ.get("REALAI_XTTS_SPEAKER") or ""
        )
        self.speaker_wav = _maybe_clip_speaker_wav(raw)
        self.base_url = (
            base_url
            or os.environ.get("REALAI_XTTS_URL")
            or "http://127.0.0.1:8020"
        ).rstrip("/")

    def _synthesize_http(self, text: str) -> bytes:
        import json
        import urllib.request

        payload_obj = {
            "text": text,
            "speaker_wav": self.speaker_wav,
            "language": os.environ.get("REALAI_XTTS_LANG", "en"),
        }
        if self.model_dir.is_dir():
            payload_obj["model_dir"] = str(self.model_dir)
        if self.model_path is not None:
            payload_obj["model_path"] = str(self.model_path)
        payload = json.dumps(payload_obj).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/tts",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read()
        if not _is_real_wav(data):
            raise RuntimeError("xtts returned empty/silent wav")
        return data

    def _ensure_local(self) -> None:
        if XTTSBackend._local_tts is not None:
            return
        if XTTSBackend._local_error:
            raise RuntimeError(XTTSBackend._local_error)
        _patch_torchaudio_load_soundfile()
        try:
            from TTS.api import TTS  # coqui-tts
            from TTS.utils.synthesizer import Synthesizer
        except Exception as exc:
            XTTSBackend._local_error = f"coqui-tts unavailable: {exc}"
            raise RuntimeError(XTTSBackend._local_error) from exc
        # XTTS local packs are multi-file dirs (model.pth + config.json + vocab…).
        # Coqui loads those via Synthesizer(model_dir=…); model_path=file.pth fails.
        cfg = self.model_dir / "config.json"
        ckpt = self.model_path if self.model_path is not None else (self.model_dir / "model.pth")
        try:
            if self.model_dir.is_dir() and cfg.is_file() and Path(ckpt).is_file():
                tts = TTS(progress_bar=False, gpu=False)
                tts.model_name = "xtts_v2_local"
                tts.synthesizer = Synthesizer(
                    model_dir=str(self.model_dir),
                    use_cuda=False,
                )
            else:
                tts = TTS(
                    model_name="tts_models/multilingual/multi-dataset/xtts_v2",
                    progress_bar=False,
                    gpu=False,
                )
        except Exception as exc:
            XTTSBackend._local_error = f"xtts load failed: {exc}"
            raise RuntimeError(XTTSBackend._local_error) from exc
        XTTSBackend._local_tts = tts

    def _synthesize_local(self, text: str) -> bytes:
        if not self.speaker_wav or not Path(self.speaker_wav).is_file():
            raise RuntimeError("xtts speaker_wav missing (set REALAI_XTTS_SPEAKER)")
        self._ensure_local()
        tts = XTTSBackend._local_tts
        assert tts is not None
        fd, path = tempfile.mkstemp(suffix=".wav", prefix="realai_xtts_")
        os.close(fd)
        out = Path(path)
        try:
            if out.exists():
                out.unlink()
            tts.tts_to_file(
                text=text,
                speaker_wav=self.speaker_wav,
                language=os.environ.get("REALAI_XTTS_LANG", "en"),
                file_path=str(out),
            )
            data = out.read_bytes()
            if not _is_real_wav(data):
                raise RuntimeError("xtts local empty/silent wav")
            return data
        finally:
            try:
                if out.exists():
                    out.unlink()
            except Exception:
                pass

    def synthesize(self, text: str) -> bytes:
        http_err: Optional[Exception] = None
        try:
            return self._synthesize_http(text)
        except Exception as exc:
            http_err = exc
        try:
            return self._synthesize_local(text)
        except Exception as local_err:
            raise RuntimeError(
                f"xtts http failed ({http_err}); local failed ({local_err})"
            ) from local_err


class WindowsSAPI:
    """Local Windows System.Speech synthesizer → WAV bytes.

    No extra packages. Works offline. Used when Kokoro/Fish/XTTS HTTP are down.
    """

    name = "windows_sapi"

    def synthesize(self, text: str) -> bytes:
        if os.name != "nt":
            raise RuntimeError("windows_sapi only available on Windows")
        spoken = (text or "").strip()
        if not spoken:
            raise RuntimeError("empty text")
        # Cap length for SAPI latency
        spoken = spoken[:1200]
        fd, path = tempfile.mkstemp(suffix=".wav", prefix="realai_sapi_")
        os.close(fd)
        out = Path(path)
        try:
            if out.exists():
                out.unlink()
            # Single-quoted PS string; escape embedded single quotes.
            safe = spoken.replace("'", "''")
            out_ps = str(out).replace("'", "''")
            ps = (
                "Add-Type -AssemblyName System.Speech; "
                "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                "$s.Rate = 0; $s.Volume = 100; "
                "$s.SetOutputToWaveFile('{out}'); "
                "$s.Speak('{text}'); "
                "$s.Dispose();"
            ).format(out=out_ps, text=safe)
            proc = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    ps,
                ],
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if proc.returncode != 0 or not out.is_file():
                err = (proc.stderr or proc.stdout or "").strip()[:300]
                raise RuntimeError(f"windows_sapi failed: {err or proc.returncode}")
            data = out.read_bytes()
            if not _is_real_wav(data):
                raise RuntimeError("windows_sapi wrote empty wav")
            return data
        finally:
            try:
                if out.exists():
                    out.unlink()
            except Exception:
                pass


class TTSEngine:
    """Speech-ready TTS with ordered backend fallback."""

    def __init__(self, backends: Optional[Iterable[TTSBackend]] = None) -> None:
        _apply_provider_config()
        preferred = (os.environ.get("REALAI_TTS_BACKEND") or "xtts").strip().lower()
        # Map aliases
        if preferred in ("sapi", "windows", "system"):
            preferred = "windows_sapi"
        built = {
            "kokoro": KokoroTTS(),
            "fish": FishSpeechTTS(),
            "xtts": XTTSBackend(),
            "windows_sapi": WindowsSAPI(),
            "piper": PiperTTS(),
        }
        if backends is not None:
            self._backends = list(backends)
        else:
            order = [preferred] + [name for name in BACKEND_ORDER if name != preferred]
            self._backends = [built[name] for name in order if name in built]
        self.persona = DEFAULT_PERSONA
        self.last_backend: Optional[str] = None
        self.last_error: Optional[str] = None

    def prepare(self, text: str) -> str:
        return prepare_speech_text(text, self.persona)

    def synthesize(self, text: str, prepare: bool = True) -> bytes:
        spoken = self.prepare(text) if prepare else (text or "").strip()
        if not spoken:
            from .tts_piper import _silent_wav

            return _silent_wav()
        last_error = None
        for backend in self._backends:
            try:
                audio = backend.synthesize(spoken)
                # Piper returns a 44-byte silent stub on failure — keep trying.
                if _is_real_wav(audio):
                    self.last_backend = getattr(backend, "name", type(backend).__name__)
                    self.last_error = None
                    return audio
                last_error = RuntimeError(
                    f"{getattr(backend, 'name', type(backend).__name__)} silent/empty wav"
                )
            except Exception as exc:
                last_error = exc
                continue
        from .tts_piper import _silent_wav

        self.last_backend = None
        self.last_error = str(last_error) if last_error else "all_backends_failed"
        return _silent_wav()

    def speak(self, text: str) -> bytes:
        """Alias for synthesize with speech prep on."""
        return self.synthesize(text, prepare=True)


def get_tts_engine() -> TTSEngine:
    return TTSEngine()

