import torch
import torch_directml
from typing import Optional

class DeviceSelector:
    """Automatically selects the best available compute device."""

    def __init__(self):
        pass

    def get_device(self) -> Optional[torch.device]:
        """Automatically selects the best available compute device."""
        try:
            dml = torch_directml.device()
            print(f"✅ Using DirectML GPU: {dml}")
            return dml
        except Exception as e:
            print(f"Error using DirectML: {e}")
            return None

        if torch.cuda.is_available():
            print("✅ Using CUDA GPU")
            return torch.device("cuda")

        print("⚠️ Using CPU")
        return torch.device("cpu")


def get_device_selector() -> DeviceSelector:
    """Returns a DeviceSelector instance."""
    return DeviceSelector()


def main():
    device_selector = get_device_selector()
    device = device_selector.get_device()
    if device is not None:
        print(f"Using device: {device}")


if __name__ == "__main__":
    main()