"""xAI / Grok Imagine media helpers — ported from Atomic Fizz backend/lib/grok.js.

Uses env XAI_API_KEY (or GROK_API_KEY). Never reads vault key files.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

XAI_BASE = "https://api.x.ai/v1"
CHAT_URL = f"{XAI_BASE}/chat/completions"
IMAGE_URL = f"{XAI_BASE}/images/generations"
VIDEO_URL = f"{XAI_BASE}/videos/generations"

DEFAULT_TEXT_MODEL = os.environ.get("GROK_TEXT_MODEL") or "grok-3"
DEFAULT_IMAGE_MODEL = os.environ.get("GROK_IMAGE_MODEL") or "grok-imagine-image"
DEFAULT_VIDEO_MODEL = os.environ.get("GROK_VIDEO_MODEL") or "grok-imagine-video"
DEFAULT_VISION_MODEL = os.environ.get("GROK_VISION_MODEL") or "grok-2-vision-latest"

POLL_INTERVAL_S = 5.0
POLL_MAX_ATTEMPTS = 12
MAX_PROMPT_CHARS = 4000


def api_key() -> Optional[str]:
    for name in ("XAI_API_KEY", "GROK_API_KEY"):
        val = (os.environ.get(name) or "").strip()
        if val:
            return val
    return None


def has_api_key() -> bool:
    return bool(api_key())


def sanitise(text: str, max_len: int = MAX_PROMPT_CHARS) -> str:
    s = re.sub(r"['\"\\`]", "", str(text or ""))
    s = re.sub(r"[\n\r]+", " ", s).strip()
    return s[:max_len]


def _request(
    method: str,
    url: str,
    body: Optional[Dict[str, Any]] = None,
    timeout: float = 120.0,
) -> Dict[str, Any]:
    key = api_key()
    if not key:
        raise RuntimeError("XAI_API_KEY (or GROK_API_KEY) is not configured")
    data = None
    headers = {
        "Authorization": f"Bearer {key}",
        "Accept": "application/json",
        "User-Agent": "RealAI-clean/atomic-fizz-xai",
    }
    if body is not None:
        raw = json.dumps(body).encode("utf-8")
        data = raw
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = resp.read().decode("utf-8", errors="replace")
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"xAI HTTP {e.code}: {err}") from e


def generate_image(
    prompt: str,
    *,
    model: Optional[str] = None,
    n: int = 1,
    size: Optional[str] = None,
) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "model": model or DEFAULT_IMAGE_MODEL,
        "prompt": sanitise(prompt),
        "n": max(1, int(n)),
    }
    if size:
        body["size"] = size
    data = _request("POST", IMAGE_URL, body)
    url = None
    if isinstance(data.get("data"), list) and data["data"]:
        url = data["data"][0].get("url") or data["data"][0].get("b64_json")
    return {"ok": True, "url": url, "raw_keys": list(data.keys()), "model": body["model"], "provider": "xai"}


def _poll_video(job_id: str) -> str:
    poll_url = f"{XAI_BASE}/videos/{job_id}"
    for attempt in range(POLL_MAX_ATTEMPTS):
        time.sleep(POLL_INTERVAL_S)
        data = _request("GET", poll_url, None, timeout=60.0)
        video = data.get("video") if isinstance(data.get("video"), dict) else None
        if video and isinstance(video.get("url"), str):
            return video["url"]
        if isinstance(data.get("url"), str):
            return data["url"]
        if isinstance(data.get("data"), list) and data["data"] and data["data"][0].get("url"):
            return str(data["data"][0]["url"])
        status = str(data.get("status") or "").lower()
        if status in {"failed", "error"}:
            raise RuntimeError(f"video job {job_id} failed: {status}")
    raise RuntimeError(f"video job {job_id} timed out")


def generate_video(
    prompt: str,
    *,
    model: Optional[str] = None,
    duration: int = 8,
    aspect: str = "16:9",
    resolution: str = "720p",
) -> Dict[str, Any]:
    body = {
        "model": model or DEFAULT_VIDEO_MODEL,
        "prompt": sanitise(prompt),
        "duration_seconds": int(duration),
        "aspect_ratio": aspect,
        "resolution": resolution,
    }
    data = _request("POST", VIDEO_URL, body, timeout=180.0)
    if isinstance(data.get("url"), str):
        return {"ok": True, "url": data["url"], "model": body["model"], "provider": "xai"}
    if isinstance(data.get("data"), list) and data["data"] and data["data"][0].get("url"):
        return {"ok": True, "url": data["data"][0]["url"], "model": body["model"], "provider": "xai"}
    job = data.get("job_id") or data.get("request_id")
    if job:
        url = _poll_video(str(job))
        return {"ok": True, "url": url, "job_id": job, "model": body["model"], "provider": "xai"}
    raise RuntimeError("video generation returned no URL or job_id")


def analyze_image(
    image_url: str,
    prompt: str = "Describe this image in detail. List notable objects and style.",
    *,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """Vision analysis via Grok multimodal chat (when key present)."""
    body = {
        "model": model or DEFAULT_VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ],
            }
        ],
        "max_tokens": 600,
        "temperature": 0.2,
    }
    data = _request("POST", CHAT_URL, body)
    content = ""
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception:
        content = json.dumps(data)[:1000]
    return {
        "ok": True,
        "description": content,
        "model": body["model"],
        "provider": "xai-vision",
        "image_url": image_url,
        "placeholder": False,
    }


def status() -> Dict[str, Any]:
    return {
        "ok": True,
        "api_key_configured": has_api_key(),
        "endpoints": {
            "chat": CHAT_URL,
            "images": IMAGE_URL,
            "videos": VIDEO_URL,
        },
        "models": {
            "text": DEFAULT_TEXT_MODEL,
            "image": DEFAULT_IMAGE_MODEL,
            "video": DEFAULT_VIDEO_MODEL,
            "vision": DEFAULT_VISION_MODEL,
        },
        "source": "Atomic Fizz backend/lib/grok.js → realai.providers.xai_media",
    }
