"""Piper-compatible TTS backend with fallback audio output."""

import subprocess
import tempfile


class PiperTTS:
    name = "piper-tts"

    def __init__(self, model_path: str = "voices/en_US-amy-medium.onnx"):
        self.model_path = model_path

    def synthesize(self, text: str) -> bytes:
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav") as tmp_file:
                subprocess.run(
                    ["piper", "--model", self.model_path, "--output_file", tmp_file.name],
                    input=text.encode("utf-8"),
                    check=True,
                    capture_output=True,
                    timeout=10,
                )
                tmp_file.seek(0)
                return tmp_file.read()
        except Exception:
            return _silent_wav()


def _silent_wav():
    # Tiny PCM WAV header + a short silence chunk.
    return (
        b"RIFF$\x00\x00\x00WAVEfmt "
        b"\x10\x00\x00\x00\x01\x00\x01\x00"
        b"\x40\x1f\x00\x00\x80>\x00\x00\x02\x00\x10\x00"
        b"data\x00\x00\x00\x00"
    )

