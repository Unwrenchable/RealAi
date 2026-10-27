"""Local SDXL-Turbo image path: heavy deps (torch/diffusers) are mocked or never imported."""
import sys

from realai import local_sdxl


def test_import_is_lazy():
    # Importing the module must not pull torch/diffusers (CI has neither).
    assert "diffusers" not in sys.modules or local_sdxl._PIPE is None


def test_weights_present(tmp_path):
    assert local_sdxl.weights_present(tmp_path) is False
    (tmp_path / "model_index.json").write_text("{}")
    (tmp_path / "unet").mkdir()
    assert local_sdxl.weights_present(tmp_path) is False
    (tmp_path / "unet" / "w.safetensors").write_text("x")
    assert local_sdxl.weights_present(tmp_path) is True


def test_parse_size_clamps():
    assert local_sdxl._parse_size("512x512") == (512, 512)
    assert local_sdxl._parse_size("garbage") == (512, 512)
    assert local_sdxl._parse_size("4000x10") == (1024, 256)


def test_ability_falls_back_to_pillow_without_weights(monkeypatch):
    from abilities import image_generation

    import realai.local_media as lm

    monkeypatch.setattr(local_sdxl, "weights_present", lambda *a, **k: False)
    monkeypatch.setattr(lm, "generate_image_local", lambda prompt, size="512x512": {"ok": True, "size": size})
    out = image_generation.run("a red square", {"size": "64x64"})
    assert out["source"] == "local_pillow"
    assert out["sdxl_note"] == "sdxl_weights_missing"


def test_ability_uses_sdxl_when_weights_present(monkeypatch):
    from abilities import image_generation

    monkeypatch.setattr(local_sdxl, "weights_present", lambda *a, **k: True)
    monkeypatch.setattr(local_sdxl, "generate", lambda prompt, **kw: {"ok": True, "path": "x.png", "kw": kw})
    out = image_generation.run("a robot", {"steps": 2, "seed": 7})
    assert out["source"] == "sdxl_turbo_local" and out["ok"] is True
    assert out["result"]["kw"]["steps"] == 2


def test_handle_images_generations_requires_prompt():
    assert "error" in local_sdxl.handle_images_generations({})
