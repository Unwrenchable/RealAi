#!/usr/bin/env python3
"""
RealAI Quick Start - Your Own AI Setup

This script helps you set up your first local AI model in minutes.
No API keys, no external dependencies - just YOUR OWN AI!
"""

import os
import sys
import subprocess
from pathlib import Path


def print_banner():
    """Print welcome banner."""
    print("=" * 80)
    print("🎉 RealAI Quick Start - Set Up YOUR OWN AI! 🎉")
    print("=" * 80)
    print("\nThis script will help you:")
    print("1. Install necessary dependencies")
    print("2. Download a local AI model")
    print("3. Configure RealAI to use it")
    print("4. Test your setup")
    print("\nLet's make you independent from external AI APIs!\n")


def check_python_version():
    """Check Python version."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 7):
        print("❌ Python 3.7+ required")
        return False
    print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    return True


def install_dependencies():
    """Install required dependencies."""
    print("\n" + "=" * 80)
    print("Step 1: Installing Dependencies")
    print("=" * 80)

    print("\nWhich backend would you like to use?")
    print("1. llama-cpp-python (Recommended - works on CPU and GPU)")
    print("2. transformers (Requires more memory, better for GPU)")
    print("3. Skip (already installed)")

    while True:
        choice = input("\nChoice (1/2/3): ").strip()
        if choice in ['1', '2', '3']:
            break
        print("Invalid choice. Please enter 1, 2, or 3.")

    if choice == '1':
        print("\nInstalling llama-cpp-python...")
        print("This may take a few minutes...")
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", "llama-cpp-python", "--quiet"
            ], check=True)
            print("✓ llama-cpp-python installed")
            return "llama-cpp"
        except subprocess.CalledProcessError:
            print("❌ Installation failed. Try manually: pip install llama-cpp-python")
            return None

    elif choice == '2':
        print("\nInstalling transformers and torch...")
        print("This may take several minutes...")
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", "transformers", "torch", "--quiet"
            ], check=True)
            print("✓ transformers and torch installed")
            return "transformers"
        except subprocess.CalledProcessError:
            print("❌ Installation failed. Try manually: pip install transformers torch")
            return None

    else:
        print("✓ Skipping installation")
        return "manual"


def check_huggingface_cli():
    """Check if huggingface-cli is available."""
    try:
        result = subprocess.run(
            ["huggingface-cli", "--version"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def install_huggingface_cli():
    """Install huggingface_hub for downloading models."""
    print("\n" + "=" * 80)
    print("Step 2: Model Download Tool")
    print("=" * 80)

    if check_huggingface_cli():
        print("\n✓ huggingface-cli is already installed")
        return True

    print("\nWe need huggingface-cli to download models.")
    response = input("Install it now? (y/n): ").strip().lower()

    if response in ['y', 'yes']:
        print("\nInstalling huggingface_hub...")
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", "huggingface_hub[cli]", "--quiet"
            ], check=True)
            print("✓ huggingface_hub installed")
            return True
        except subprocess.CalledProcessError:
            print("❌ Installation failed")
            return False
    else:
        print("⚠ Skipping. You'll need to download models manually.")
        return False


def suggest_models():
    """Suggest models based on user's hardware."""
    print("\n" + "=" * 80)
    print("Step 3: Choose a Model")
    print("=" * 80)

    print("\nHow much RAM do you have available?")
    print("1. 4-8 GB  (Low-end, CPU only)")
    print("2. 8-16 GB (Mid-range)")
    print("3. 16+ GB  (High-end, GPU available)")

    while True:
        choice = input("\nChoice (1/2/3): ").strip()
        if choice in ['1', '2', '3']:
            break

    models = {
        '1': {
            'name': 'llama3.2-1b',
            'repo': 'bartowski/Llama-3.2-1B-Instruct-GGUF',
            'file': '*Q4_K_M.gguf',
            'size': '~1 GB',
            'desc': 'Llama 3.2 1B - Fast, works great on CPU'
        },
        '2': {
            'name': 'llama3.2-3b',
            'repo': 'bartowski/Llama-3.2-3B-Instruct-GGUF',
            'file': '*Q4_K_M.gguf',
            'size': '~2 GB',
            'desc': 'Llama 3.2 3B - Great balance of speed and quality'
        },
        '3': {
            'name': 'mistral-7b',
            'repo': 'TheBloke/Mistral-7B-Instruct-v0.2-GGUF',
            'file': '*Q4_K_M.gguf',
            'size': '~4 GB',
            'desc': 'Mistral 7B - High quality, needs GPU for speed'
        }
    }

    model = models[choice]
    print(f"\nRecommended: {model['desc']}")
    print(f"Size: {model['size']}")

    return model


def download_model(model_info, has_hf_cli):
    """Download the model."""
    print("\n" + "=" * 80)
    print("Step 4: Downloading Model")
    print("=" * 80)

    if not has_hf_cli:
        print("\n⚠ huggingface-cli not available")
        print(f"\nTo download manually:")
        print(f"1. Install: pip install huggingface_hub[cli]")
        print(f"2. Download: huggingface-cli download {model_info['repo']} --include '{model_info['file']}'")
        print(f"3. Run this script again")
        return None

    models_dir = Path.home() / ".realai" / "models" / model_info['name']
    models_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nDownloading {model_info['desc']}...")
    print(f"This will take a while (downloading {model_info['size']})...")
    print("You can grab a coffee ☕\n")

    try:
        result = subprocess.run([
            "huggingface-cli", "download",
            model_info['repo'],
            "--include", model_info['file'],
            "--local-dir", str(models_dir)
        ], check=True, capture_output=True, text=True)

        # Find the downloaded GGUF file
        gguf_files = list(models_dir.rglob("*.gguf"))
        if gguf_files:
            print(f"\n✓ Model downloaded to: {gguf_files[0]}")
            return gguf_files[0]
        else:
            print("\n❌ Model file not found after download")
            return None

    except subprocess.CalledProcessError as e:
        print(f"\n❌ Download failed: {e}")
        print("\nTry downloading manually:")
        print(f"huggingface-cli download {model_info['repo']} --include '{model_info['file']}'")
        return None


def register_model(model_name, model_path):
    """Register the model with RealAI."""
    print("\n" + "=" * 80)
    print("Step 5: Registering Model")
    print("=" * 80)

    try:
        # Import here to avoid issues if not installed
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from local_models import get_model_manager, LocalModelType

        manager = get_model_manager()

        config = {
            "path": str(model_path),
            "backend": "llama-cpp",
            "context_length": 2048,
            "gpu_layers": -1,  # Use all available GPU layers
        }

        manager.register_model(model_name, LocalModelType.LLM, config)
        manager.config["default_llm"] = model_name
        manager._save_config()

        print(f"\n✓ Model '{model_name}' registered and set as default")
        return True

    except Exception as e:
        print(f"\n❌ Registration failed: {e}")
        print(f"\nRegister manually:")
        print(f"python local_model_cli.py register {model_name} {model_path}")
        return False


def test_model(model_name):
    """Test the model."""
    print("\n" + "=" * 80)
    print("Step 6: Testing Your AI")
    print("=" * 80)

    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from realai import RealAIClient

        print("\nInitializing your local AI...")
        client = RealAIClient(provider="local")

        print("Generating test response...")
        print("-" * 80)

        response = client.chat.create(
            messages=[
                {"role": "user", "content": "Hello! Introduce yourself in one sentence."}
            ],
            max_tokens=100
        )

        print(f"\nYour AI: {response['choices'][0]['message']['content']}")
        print("-" * 80)
        print(f"\n✓ SUCCESS! Your AI is working!")
        print(f"Model: {response.get('model', 'unknown')}")
        print(f"Source: {response.get('realai_meta', {}).get('source', 'unknown')}")

        return True

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("\nTry testing manually:")
        print(f"python local_model_cli.py test {model_name}")
        return False


def show_next_steps():
    """Show what to do next."""
    print("\n" + "=" * 80)
    print("🎉 Congratulations! You're now running YOUR OWN AI! 🎉")
    print("=" * 80)

    print("\n✨ What you've achieved:")
    print("  • Your AI runs completely locally")
    print("  • No API keys or external dependencies")
    print("  • Your data stays private on your machine")
    print("  • Zero ongoing costs")
    print("  • Full control and customization")

    print("\n🚀 Next Steps:")
    print("\n1. Try the examples:")
    print("   python examples_local_ai.py")

    print("\n2. Use in your code:")
    print("   from realai import RealAIClient")
    print("   client = RealAIClient(provider='local')")
    print("   response = client.chat.create(messages=[...])")

    print("\n3. Manage models:")
    print("   python local_model_cli.py list       # List models")
    print("   python local_model_cli.py config     # Show config")
    print("   python local_model_cli.py download   # Get more models")

    print("\n4. Read the guide:")
    print("   cat LOCAL_AI_GUIDE.md")

    print("\n💡 You are now YOUR OWN AI - not a copy of another API!")
    print("   Welcome to true AI independence! 🎊")


def main():
    """Run the quick start setup."""
    print_banner()

    # Check Python version
    if not check_python_version():
        return 1

    # Install dependencies
    backend = install_dependencies()
    if backend is None:
        print("\n⚠ Setup incomplete. Please install dependencies manually.")
        return 1

    # Install HF CLI
    has_hf_cli = install_huggingface_cli()

    # Choose model
    model_info = suggest_models()

    # Download model
    response = input(f"\nDownload {model_info['desc']} now? (y/n): ").strip().lower()
    if response not in ['y', 'yes']:
        print("\n⚠ Setup incomplete. Download a model to continue.")
        print(f"\nDownload manually:")
        print(f"huggingface-cli download {model_info['repo']} --include '{model_info['file']}'")
        return 1

    model_path = download_model(model_info, has_hf_cli)
    if not model_path:
        return 1

    # Register model
    if not register_model(model_info['name'], model_path):
        return 1

    # Test model
    if not test_model(model_info['name']):
        print("\n⚠ Model registered but test failed. You can still use it.")

    # Show next steps
    show_next_steps()

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
