"""Local-first media helpers so image/video/vision abilities stay LIVE without XAI.

Pillow procedural generation + analysis. Optional xAI path stays preferred when keyed.
"""
from __future__ import annotations

import colorsys
import hashlib
import io
import math
import re
import struct
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_OUT = Path(__file__).resolve().parents[1] / "scan_results" / "local_media"
_OUT.mkdir(parents=True, exist_ok=True)


def _seed_from(prompt: str) -> int:
    h = hashlib.sha256((prompt or "realai").encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def _palette(seed: int) -> List[Tuple[int, int, int]]:
    colors: List[Tuple[int, int, int]] = []
    for i in range(5):
        h = ((seed >> (i * 5)) % 360) / 360.0
        s = 0.45 + ((seed >> (i * 3)) % 40) / 100.0
        v = 0.55 + ((seed >> (i * 7)) % 35) / 100.0
        r, g, b = colorsys.hsv_to_rgb(h, min(s, 1.0), min(v, 1.0))
        colors.append((int(r * 255), int(g * 255), int(b * 255)))
    return colors


def generate_image_local(
    prompt: str,
    *,
    size: str = "512x512",
    out_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Render a deterministic procedural PNG from the prompt (no cloud)."""
    from PIL import Image, ImageDraw, ImageFont

    m = re.match(r"(\d+)\s*[xX]\s*(\d+)", str(size or "512x512"))
    w, h = (int(m.group(1)), int(m.group(2))) if m else (512, 512)
    w = max(64, min(w, 1280))
    h = max(64, min(h, 1280))
    seed = _seed_from(prompt)
    palette = _palette(seed)
    img = Image.new("RGB", (w, h), palette[0])
    draw = ImageDraw.Draw(img)

    # Background gradient bands
    for y in range(h):
        t = y / max(h - 1, 1)
        c0, c1 = palette[0], palette[1]
        col = tuple(int(c0[i] * (1 - t) + c1[i] * t) for i in range(3))
        draw.line([(0, y), (w, y)], fill=col)

    # Geometric motifs driven by prompt tokens
    tokens = re.findall(r"[a-zA-Z0-9]+", prompt.lower()) or ["realai"]
    for i, tok in enumerate(tokens[:12]):
        th = hashlib.md5(f"{seed}:{tok}:{i}".encode()).hexdigest()
        x = int(th[:4], 16) % w
        y = int(th[4:8], 16) % h
        r = 20 + (int(th[8:10], 16) % 80)
        col = palette[2 + (i % 3)]
        shape = int(th[10:12], 16) % 3
        if shape == 0:
            draw.ellipse([x - r, y - r, x + r, y + r], outline=col, width=3)
        elif shape == 1:
            draw.rectangle([x - r, y - r, x + r, y + r], outline=col, width=3)
        else:
            draw.polygon(
                [(x, y - r), (x + r, y + r), (x - r, y + r)],
                outline=col,
            )

    # Title plate
    title = (prompt or "RealAI").strip()[:48]
    pad = 12
    box_h = 54
    draw.rectangle([0, h - box_h, w, h], fill=(12, 12, 28))
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    draw.text((pad, h - box_h + 18), f"RealAI · {title}", fill=palette[3], font=font)

    out_root = Path(out_dir) if out_dir else _OUT
    out_root.mkdir(parents=True, exist_ok=True)
    name = f"img_{seed:08x}.png"
    path = out_root / name
    img.save(path, format="PNG")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = __import__("base64").b64encode(buf.getvalue()).decode("ascii")
    return {
        "ok": True,
        "backend": "local_pillow",
        "path": str(path),
        "width": w,
        "height": h,
        "prompt": prompt,
        "format": "png",
        "bytes": path.stat().st_size,
        "b64_prefix": b64[:80] + "…",
        "image_b64": b64 if len(b64) < 400_000 else None,
    }


def generate_video_local(
    prompt: str,
    *,
    frames: int = 12,
    size: str = "320x240",
    out_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Render a short animated GIF (local stand-in for cloud video)."""
    from PIL import Image, ImageDraw

    m = re.match(r"(\d+)\s*[xX]\s*(\d+)", str(size or "320x240"))
    w, h = (int(m.group(1)), int(m.group(2))) if m else (320, 240)
    w = max(64, min(w, 640))
    h = max(64, min(h, 480))
    frames = max(4, min(int(frames or 12), 36))
    seed = _seed_from(prompt)
    palette = _palette(seed)
    imgs: List[Any] = []
    for fi in range(frames):
        img = Image.new("RGB", (w, h), palette[0])
        draw = ImageDraw.Draw(img)
        for y in range(h):
            t = (y / max(h - 1, 1) + fi / frames) % 1.0
            c0, c1 = palette[0], palette[1]
            col = tuple(int(c0[i] * (1 - t) + c1[i] * t) for i in range(3))
            draw.line([(0, y), (w, y)], fill=col)
        cx = int(w * (0.3 + 0.4 * (0.5 + 0.5 * math.sin(2 * math.pi * fi / frames))))
        cy = int(h * (0.4 + 0.2 * math.cos(2 * math.pi * fi / frames)))
        r = 18 + (fi % 8)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=palette[2], outline=palette[3], width=2)
        draw.rectangle([0, h - 28, w, h], fill=(10, 10, 22))
        draw.text((8, h - 22), f"RealAI · {(prompt or '')[:28]}", fill=palette[4])
        imgs.append(img)

    out_root = Path(out_dir) if out_dir else _OUT
    out_root.mkdir(parents=True, exist_ok=True)
    path = out_root / f"vid_{seed:08x}.gif"
    imgs[0].save(
        path,
        save_all=True,
        append_images=imgs[1:],
        duration=90,
        loop=0,
        format="GIF",
    )
    return {
        "ok": True,
        "backend": "local_pillow_gif",
        "path": str(path),
        "frames": frames,
        "width": w,
        "height": h,
        "prompt": prompt,
        "format": "gif",
        "bytes": path.stat().st_size,
        "note": "Local animated GIF — set XAI_API_KEY for cloud Imagine Video",
    }


def analyze_image_local(image_ref: str) -> Dict[str, Any]:
    """Analyze a local path or downloadable URL with Pillow (real pixels, not placeholder)."""
    from PIL import Image, ImageStat
    import urllib.request

    raw: Optional[bytes] = None
    source = image_ref
    p = Path(image_ref)
    if p.is_file():
        raw = p.read_bytes()
        source = str(p.resolve())
    elif image_ref.startswith("data:image"):
        import base64

        try:
            b64 = image_ref.split(",", 1)[1]
            raw = base64.b64decode(b64)
            source = "data_uri"
        except Exception as e:
            return {"ok": False, "error": f"bad_data_uri:{e}"}
    elif image_ref.startswith("http://") or image_ref.startswith("https://"):
        try:
            req = urllib.request.Request(
                image_ref,
                headers={"User-Agent": "RealAI-local-media/1.0"},
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read()
        except Exception as e:
            return {
                "ok": False,
                "error": f"fetch_failed:{e}",
                "hint": "Pass a local file path for offline analysis",
            }
    else:
        return {"ok": False, "error": "image_not_found", "image_ref": image_ref}

    assert raw is not None
    img = Image.open(io.BytesIO(raw))
    img.load()
    rgb = img.convert("RGB")
    stat = ImageStat.Stat(rgb)
    # Dominant-ish colors via resize
    thumb = rgb.resize((32, 32))
    colors = thumb.getcolors(32 * 32) or []
    colors.sort(key=lambda x: x[0], reverse=True)
    top = [
        {"count": c, "rgb": list(col)}
        for c, col in colors[:5]
    ]
    extrema = rgb.getextrema()
    description = (
        f"Local vision analysis of {source}: mode={img.mode}, size={img.size[0]}x{img.size[1]}, "
        f"format={getattr(img, 'format', None)}, mean_rgb={[round(x,1) for x in stat.mean]}, "
        f"top_colors={len(top)}. "
        f"Brightness≈{sum(stat.mean)/3:.1f}/255."
    )
    return {
        "ok": True,
        "backend": "local_pillow",
        "placeholder": False,
        "source": source,
        "description": description,
        "width": img.size[0],
        "height": img.size[1],
        "mode": img.mode,
        "format": getattr(img, "format", None),
        "mean_rgb": [round(x, 2) for x in stat.mean],
        "stddev_rgb": [round(x, 2) for x in stat.stddev],
        "extrema": extrema,
        "top_colors": top,
        "bytes": len(raw),
    }


def hive_chat(prompt: str, *, system: str, max_tokens: int = 256) -> Dict[str, Any]:
    """Call local Hive chat for specialist text abilities."""
    import json
    import urllib.request

    body = json.dumps(
        {
            "model": "realai-default-coder",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.35,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:8001/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "X-RealAI-Tools": "off"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
    text = (
        ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
    )
    return {"ok": True, "text": text, "model": data.get("model"), "raw_id": data.get("id")}
