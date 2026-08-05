"""
RealAI Device Selector Plugin
Automatically chooses the best compute device (DirectML, CUDA, CPU).
Recovered from realai2/plugins/tools/device_selector.py
"""

from __future__ import annotations

from typing import Any

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None  # type: ignore
    TORCH_AVAILABLE = False

try:
    import torch_directml
    DIRECTML_AVAILABLE = True
except ImportError:
    DIRECTML_AVAILABLE = False


class DeviceSelector:
    """Plugin for selecting the best available device."""

    def get_device(self) -> Any:
        """Return the best available torch device (or string if no torch)."""
        if DIRECTML_AVAILABLE and TORCH_AVAILABLE:
            try:
                dml = torch_directml.device()
                return dml
            except Exception:
                pass
        if TORCH_AVAILABLE and torch.cuda.is_available():
            return torch.device("cuda")
        if TORCH_AVAILABLE:
            return torch.device("cpu")
        return "cpu"

    def get_device_name(self) -> str:
        if DIRECTML_AVAILABLE:
            return "directml"
        if TORCH_AVAILABLE and torch.cuda.is_available():
            return "cuda"
        return "cpu"


device_selector = DeviceSelector()


def get_device():
    return device_selector.get_device()


def get_device_name():
    return device_selector.get_device_name()
