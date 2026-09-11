"""Thin wrap over ``realai.plugins.tools.device_selector.DeviceSelector``."""

from __future__ import annotations

from typing import Any

ABILITY = {
    "id": "device_selector",
    "name": "device_selector",
    "type": "ability",
    "status": "CODE",
    "source": "realai.plugins.tools.device_selector",
    "dest": "abilities/device_selector.py",
    "capabilities": ["device", "directml", "cuda", "cpu"],
    "secrets_policy": "none",
}


def run(
    input: str = "",
    context: dict[str, Any] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    from realai.plugins.tools.device_selector import (
        DIRECTML_AVAILABLE,
        TORCH_AVAILABLE,
        DeviceSelector,
    )

    sel = DeviceSelector()
    device = sel.get_device()
    return {
        "ok": True,
        "ability": "device_selector",
        "device": str(device),
        "torch_available": TORCH_AVAILABLE,
        "directml_available": DIRECTML_AVAILABLE,
        "input": input,
    }
