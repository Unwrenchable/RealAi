"""
Local embeddings + audio handlers recovered from kilo/realai2 era.

Originally a Lambda-style router; adapted for RealAI v3 orchestrator:
  - embeddings → realai.server.embeddings_backend (deterministic / ST fallback)
  - audio → honest stubs until local ASR/TTS deps are installed

Public helpers used by v3_orchestrator:
  create_embeddings_response(body) -> OpenAI-ish embeddings dict
  create_transcription_response(body)
  create_speech_response(body)
"""

from __future__ import annotations

import time
from typing import Any, Dict, List


def _as_texts(value: Any) -> List[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out = []
        for item in value:
            if isinstance(item, str):
                out.append(item)
            else:
                out.append(str(item))
        if not out:
            raise ValueError("input must be non-empty")
        return out
    raise ValueError("input must be a string or list of strings")


def create_embeddings_response(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build OpenAI-compatible embeddings payload using local backend.
    Prefer deterministic (always available); try sentence-transformers if path set.
    """
    texts = _as_texts(body.get("input", ""))
    model = str(body.get("model") or "realai-embeddings")
    backend_hint = str(body.get("backend") or "deterministic")
    model_path = str(body.get("model_path") or body.get("path") or model)

    try:
        from realai.server.embeddings_backend import EMBEDDING_RESOLVER
        vectors, backend_name = EMBEDDING_RESOLVER.embed(backend_hint, model_path, texts)
    except Exception as e:
        import hashlib
        import math

        vectors = []
        for text in texts:
            seed = hashlib.sha256(f"{model}:{text}".encode()).digest()
            vals = []
            cur = seed
            while len(vals) < 64:
                for i in range(0, len(cur), 4):
                    chunk = cur[i : i + 4]
                    if len(chunk) < 4:
                        break
                    raw = int.from_bytes(chunk, "big")
                    vals.append((raw / 4294967295.0) * 2.0 - 1.0)
                    if len(vals) >= 64:
                        break
                cur = hashlib.sha256(cur).digest()
            norm = math.sqrt(sum(v * v for v in vals)) or 1.0
            vectors.append([round(v / norm, 8) for v in vals[:64]])
        backend_name = f"inline-deterministic({e})"

    dims = len(vectors[0]) if vectors else 0
    return {
        "object": "list",
        "model": model,
        "data": [
            {"object": "embedding", "index": i, "embedding": vec}
            for i, vec in enumerate(vectors or [])
        ],
        "usage": {
            "prompt_tokens": sum(max(1, len(t.split())) for t in texts),
            "total_tokens": sum(max(1, len(t.split())) for t in texts),
        },
        "realai": {
            "backend": backend_name,
            "dimensions": dims,
            "provider": "realai-v3-local",
            "source": "lambda_embeddings_audio (recovered+adapted)",
        },
    }


def create_transcription_response(body: Dict[str, Any]) -> Dict[str, Any]:
    """ASR stub — recovered Lambda path; real local ASR not bundled."""
    audio_file = body.get("file") or body.get("audio_file") or ""
    return {
        "text": (
            f"[RealAI ASR stub] file={audio_file or 'none'}; "
            "install whisper/vosk for live transcription"
        ),
        "language": body.get("language") or "en",
        "realai": {
            "status": "stub",
            "source": "lambda_embeddings_audio (recovered)",
            "next": "wire local whisper or vosk under realai/server",
        },
    }


def create_speech_response(body: Dict[str, Any]) -> Dict[str, Any]:
    """TTS stub — recovered Lambda path."""
    text = body.get("input") or body.get("text") or ""
    return {
        "created": int(time.time()),
        "voice": body.get("voice") or "alloy",
        "format": body.get("response_format") or body.get("format") or "mp3",
        "text_echo": text[:500],
        "audio_url": None,
        "realai": {
            "status": "stub",
            "source": "lambda_embeddings_audio (recovered)",
            "next": "wire local pyttsx3/piper for live TTS",
        },
    }


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    """Minimal AWS-Lambda-shaped entry for tests/compat."""
    import json

    path = event.get("path") or ""
    method = (event.get("httpMethod") or "POST").upper()
    if method == "OPTIONS":
        return {"statusCode": 204, "headers": {"Access-Control-Allow-Origin": "*"}, "body": ""}
    body: Dict[str, Any] = {}
    raw = event.get("body")
    if isinstance(raw, str) and raw:
        try:
            body = json.loads(raw)
        except Exception:
            return {"statusCode": 400, "body": '{"error":"invalid_json"}'}
    elif isinstance(raw, dict):
        body = raw
    try:
        if path.endswith("/embeddings") or path == "/v1/embeddings":
            out = create_embeddings_response(body)
        elif "transcription" in path:
            out = create_transcription_response(body)
        elif "speech" in path:
            out = create_speech_response(body)
        else:
            return {"statusCode": 404, "body": '{"error":"not_found"}'}
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps(out),
        }
    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
