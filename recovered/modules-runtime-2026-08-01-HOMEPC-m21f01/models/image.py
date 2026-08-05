import os
import textwrap
from typing import Any, Dict, Optional

import torch

from realai.hf_compat import ensure_huggingface_hub_compat

ensure_huggingface_hub_compat()

try:
    from diffusers import DiffusionPipeline
    DIFFUSERS_AVAILABLE = True
except ImportError:
    DiffusionPipeline = None
    DIFFUSERS_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    Image = None
    ImageDraw = None
    ImageFont = None
    PIL_AVAILABLE = False

class ImageModel:
    def __init__(self, model_path: str, device: str = "cuda"):
        self.model_path = model_path
        self.device = device
        self.pipe = None
        self.loaded_model_id = None
        self.is_local_sdxl = False

        if self.device == "cuda" and not torch.cuda.is_available():
            print("[RealAI] CUDA not available. Falling back to CPU for image generation.")
            self.device = "cpu"
        if self.device == "mps":
            try:
                if not (hasattr(torch.backends, "mps") and torch.backends.mps.is_available()):
                    print("[RealAI] MPS not available. Falling back to CPU for image generation.")
                    self.device = "cpu"
            except Exception:
                self.device = "cpu"

        print(f"[RealAI] Loading image model: {model_path}")
        if DIFFUSERS_AVAILABLE:
            self._load_pipeline_with_fallbacks(model_path)
        else:
            print("[RealAI] Diffusers not available. Using placeholder image generation.")

    def generate(self, prompt: str, **kwargs) -> Any:
        if self.pipe is None:
            return self._generate_placeholder(prompt)

        num_inference_steps = int(kwargs.get("num_inference_steps", 20))
        guidance_scale = float(kwargs.get("guidance_scale", 7.5))
        result = self.pipe(
            prompt,
            num_inference_steps=num_inference_steps,
            guidance_scale=guidance_scale,
        )
        return result.images[0]

    def generate_video_sequence(
        self,
        prompt: str,
        world_context: Optional[str] = None,
        num_frames: int = 8,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a simple 'video' as a sequence of images (with light variation for motion).
        This is the practical starting point for RealAI-native video.
        World context (memory, game state, lore) is injected for consistency.
        Returns list of PIL images or paths + metadata.
        Later: integrate real video diffusion or agent-orchestrated rendering.
        """
        frames = []
        base_prompt = prompt
        if world_context:
            base_prompt = f"{prompt}. Context: {world_context[:300]}"

        if self.pipe is None:
            # placeholder sequence
            for i in range(max(1, int(num_frames))):
                frames.append(self._generate_placeholder(f"{base_prompt} [frame {i}]"))
            return {
                "status": "success",
                "frames": len(frames),
                "backend": "placeholder-sequence",
                "images": frames,
                "note": "Install diffusers for real frames. This is a text-rendered sequence.",
            }

        num_inference_steps = int(kwargs.get("num_inference_steps", 18))
        guidance_scale = float(kwargs.get("guidance_scale", 7.0))
        seed = kwargs.get("seed")

        for i in range(max(1, int(num_frames))):
            frame_prompt = f"{base_prompt}, frame {i+1} of {num_frames}, slight motion"
            if seed is not None:
                # simple per-frame seed variation
                generator = torch.Generator(device=self.device).manual_seed(int(seed) + i)
                try:
                    out = self.pipe(
                        frame_prompt,
                        num_inference_steps=num_inference_steps,
                        guidance_scale=guidance_scale,
                        generator=generator,
                    )
                except Exception:
                    out = self.pipe(frame_prompt, num_inference_steps=num_inference_steps, guidance_scale=guidance_scale)
            else:
                out = self.pipe(frame_prompt, num_inference_steps=num_inference_steps, guidance_scale=guidance_scale)
            frames.append(out.images[0])

        return {
            "status": "success",
            "frames": len(frames),
            "backend": "local-diffusers-sequence",
            "model": getattr(self, "loaded_model_id", None),
            "images": frames,
            "prompt": prompt,
            "world_context_used": bool(world_context),
        }

    def _load_pipeline_with_fallbacks(self, primary_model_id: str) -> None:
        allow_remote_download = _env_bool("REALAI_IMAGE_ALLOW_REMOTE_DOWNLOAD", default=True)
        prefer_primary_remote = _env_bool("REALAI_IMAGE_PREFER_PRIMARY_REMOTE", default=False)

        # Strategy:
        # 1) If primary looks like a local dir with model_index.json (e.g. models/image for SDXL), load directly as local.
        # 2) Try primary model from local cache first to avoid giant first-request downloads.
        # 3) If unavailable, try tiny fallback with remote allowed.
        # 4) Optionally try primary with remote if explicitly requested.
        candidates = [primary_model_id]
        local_sdxl_path = None

        # Detect local RealAI SDXL structure (models/image with model_index.json + components)
        if os.path.isdir(primary_model_id) and os.path.exists(os.path.join(primary_model_id, "model_index.json")):
            local_sdxl_path = primary_model_id
            print(f"[RealAI] Detected local SDXL-style model dir: {primary_model_id}")
            self.is_local_sdxl = True
        elif primary_model_id in ("realai-image", "realai-vision", "local-sdxl", "models/image"):
            candidate_local = os.path.join(os.path.dirname(__file__), "..", "..", "models", "image")
            candidate_local = os.path.abspath(candidate_local)
            if os.path.exists(os.path.join(candidate_local, "model_index.json")):
                local_sdxl_path = candidate_local
                self.is_local_sdxl = True
                print(f"[RealAI] Using bundled local SDXL assets from {local_sdxl_path}")

        tiny_fallback = os.environ.get(
            "REALAI_IMAGE_TINY_FALLBACK_MODEL",
            "hf-internal-testing/tiny-stable-diffusion-pipe",
        )
        if tiny_fallback and tiny_fallback not in candidates:
            candidates.append(tiny_fallback)
        if prefer_primary_remote and primary_model_id not in candidates:
            candidates.append(primary_model_id)

        dtype = (
            torch.float16
            if self.device in ("cuda", "mps")
            else torch.float32
        )

        last_error = None

        # Prefer direct local SDXL load if we found a valid dir
        if local_sdxl_path:
            try:
                # Use the model_index to load as StableDiffusionXLPipeline explicitly if possible
                self.pipe = DiffusionPipeline.from_pretrained(
                    local_sdxl_path,
                    torch_dtype=dtype,
                    local_files_only=True,
                ).to(self.device)
                if hasattr(self.pipe, "safety_checker"):
                    self.pipe.safety_checker = None
                if hasattr(self.pipe, "requires_safety_checker"):
                    self.pipe.requires_safety_checker = False
                self.loaded_model_id = local_sdxl_path
                print(f"[RealAI] Image model ready (local SDXL): {local_sdxl_path}")
                return
            except Exception as exc:
                last_error = exc
                print(f"[RealAI] Local SDXL load failed ({local_sdxl_path}), will try fallbacks: {exc}")

        for model_id in candidates:
            if model_id == local_sdxl_path:
                continue  # already tried
            # Only use local cache for the primary model by default.
            local_files_only = True if model_id == primary_model_id and not prefer_primary_remote else (not allow_remote_download)
            try:
                self.pipe = DiffusionPipeline.from_pretrained(
                    model_id,
                    torch_dtype=dtype,
                    local_files_only=local_files_only,
                ).to(self.device)
                if hasattr(self.pipe, "safety_checker"):
                    self.pipe.safety_checker = None
                if hasattr(self.pipe, "requires_safety_checker"):
                    self.pipe.requires_safety_checker = False
                self.loaded_model_id = model_id
                print(f"[RealAI] Image model ready: {model_id}")
                return
            except Exception as exc:
                last_error = exc
                print(f"[RealAI] Image model load failed for {model_id}: {exc}")

        self.pipe = None
        self.loaded_model_id = None
        if last_error is not None:
            print("[RealAI] Falling back to placeholder image generation.")

    def _generate_placeholder(self, prompt: str) -> Any:
        if not PIL_AVAILABLE:
            encoded = textwrap.fill(prompt.strip() or "No prompt provided.", width=60)
            return {
                "status": "fallback",
                "note": "Pillow is not installed, so no image object can be created.",
                "prompt": prompt,
                "preview_text": encoded,
            }

        image = Image.new("RGB", (1024, 1024), color=(18, 18, 24))
        draw = ImageDraw.Draw(image)
        try:
            font = ImageFont.truetype("arial.ttf", 28)
        except Exception:
            font = ImageFont.load_default()

        title = "RealAI image fallback"
        wrapped_prompt = textwrap.fill(prompt.strip() or "No prompt provided.", width=42)
        draw.text((48, 48), title, fill=(240, 240, 255), font=font)
        draw.multiline_text((48, 110), wrapped_prompt, fill=(200, 200, 220), font=font, spacing=8)
        draw.text((48, 960), "Install diffusers + a compatible huggingface_hub to enable generation.", fill=(140, 140, 160), font=font)
        return image


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")
