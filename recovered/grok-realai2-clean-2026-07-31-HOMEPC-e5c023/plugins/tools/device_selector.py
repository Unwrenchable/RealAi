"""
RealAI Device Selector Plugin
Automatically chooses the best compute device (DirectML, CUDA, CPU).
"""

import torch
try:
    import torch_directml
    DIRECTML_AVAILABLE = True
except ImportError:
    DIRECTML_AVAILABLE = False

class DeviceSelector:
    """Plugin for selecting the best available device."""
    
    def get_device(self):
        """Return the best available torch device."""
        if DIRECTML_AVAILABLE:
            try:
                dml = torch_directml.device()
                print(f"✅ Using DirectML GPU: {dml}")
                return dml
            except:
                pass
        
        if torch.cuda.is_available():
            print(f"✅ Using CUDA GPU: {torch.cuda.get_device_name(0)}")
            return torch.device("cuda")
        
        print("⚠️  Using CPU (no GPU detected)")
        return torch.device("cpu")

    def get_device_name(self) -> str:
        if DIRECTML_AVAILABLE:
            return "directml"
        elif torch.cuda.is_available():
            return "cuda"
        return "cpu"

# Global instance
device_selector = DeviceSelector()

def get_device():
    return device_selector.get_device()

def get_device_name():
    return device_selector.get_device_name()