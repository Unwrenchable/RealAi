"""model_catalog: reads never write the registry; missing weights never drop ids."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from realai.models import model_catalog as mc

_REPO = Path(__file__).resolve().parents[1]
_TRACKED = (_REPO / "realai" / "config" / "realai_models.json", _REPO / "config" / "realai_models.json")


def _ids(path: Path):
    return [m["id"] for m in json.loads(path.read_text(encoding="utf-8"))["models"]]


def test_build_catalog_is_read_only():
    with patch.object(mc, "save_registry") as save, patch.object(mc, "vulkan_loaded_model_ids", return_value=[]):
        mc.build_catalog()
        mc.openai_models_payload()
        mc.resolve_model_for_backend("realai-hive")
    save.assert_not_called()


def test_registered_ids_survive_missing_weights():
    registered = set(_ids(mc._REGISTRY))
    with patch.object(mc, "vulkan_loaded_model_ids", return_value=[]):
        cat = mc.build_catalog()
    got = {m["id"]: m for m in cat["data"]}
    assert registered <= set(got), sorted(registered - set(got))
    for mid in registered:
        assert "available" in got[mid]["realai"], mid


def test_default_model_unchanged():
    with patch.object(mc, "vulkan_loaded_model_ids", return_value=[]):
        cat = mc.build_catalog()
    assert cat["realai"]["default_model"] == "realai-hive"


def test_refresh_registry_merges_and_never_drops(tmp_path):
    pkg, prod = tmp_path / "a.json", tmp_path / "b.json"
    pkg.write_text(json.dumps({"models": [
        {"id": "keep-me", "gguf_path": str(tmp_path / "gone.gguf"), "family": "local", "base_model": "x/y"},
    ]}), encoding="utf-8")
    with patch.object(mc, "_REGISTRY", pkg), patch.object(mc, "_PRODUCT_REGISTRY", prod), \
            patch.object(mc, "vulkan_loaded_model_ids", return_value=[]):
        mc.refresh_registry()
    rows = {r["id"]: r for r in json.loads(pkg.read_text(encoding="utf-8"))["models"]}
    assert rows["keep-me"]["available"] is False
    assert rows["keep-me"]["base_model"] == "x/y"
    assert "realai-hive" in rows
    assert prod.is_file()


def test_tracked_registry_labels():
    for path in _TRACKED:
        rows = {r["id"]: r for r in json.loads(path.read_text(encoding="utf-8"))["models"]}
        assert len(rows) >= 66
        for stock in ("realai-1.0-instruct", "realai-overseer"):
            assert rows[stock]["base_model"] == "meta-llama/Llama-3.2-1B-Instruct"
            assert rows[stock]["trained"] is False
        assert "loss" in rows["realai-1.5b-hive-expand-32"]["note"]
        assert rows["realai-lora-1.5b"]["gguf_path"].endswith(
            r"lora\qwen2.5-1.5b-lora-realai-export\qwen2.5-1.5b-lora-realai-Q5_K_M.gguf")
        loras = [r for r in rows.values() if r["id"].endswith("-default-run")]
        assert len(loras) == 40
        assert all("agent_lora_runs" in r["adapter_path"] for r in loras)
