"""Quick-start script for RealAI local llama.cpp inference.

This script helps set up and verify your local llama.cpp integration.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path


def check_llama_cli():
    """Check if llama-cli is available."""
    print("🔍 Checking for llama-cli...")

    llama_cli = shutil.which('llama-cli') or shutil.which('llama-cli.exe')
    if llama_cli:
        print(f"   ✅ Found llama-cli: {llama_cli}")
        return Path(llama_cli)

    # Check common locations
    common_paths = [
        Path.home() / 'llama.cpp' / 'build' / 'bin' / 'Release' / 'llama-cli.exe',
        Path('C:/llama.cpp/build/bin/Release/llama-cli.exe'),
        Path('C:/llama.cpp/llama-cli.exe'),
    ]

    for path in common_paths:
        if path.exists():
            print(f"   ✅ Found llama-cli: {path}")
            return path

    print("   ❌ llama-cli not found in PATH")
    print("\n📥 Download llama.cpp from: https://github.com/ggerganov/llama.cpp/releases")
    print("   Or build from source: https://github.com/ggerganov/llama.cpp#build")
    return None


def check_gguf_models():
    """Check for GGUF models."""
    print("\n🔍 Checking for GGUF models...")

    common_dirs = [
        Path.home() / 'models',
        Path('C:/Users/tsmit/models'),
        Path.cwd() / 'models',
    ]

    found_models = []
    for model_dir in common_dirs:
        if model_dir.exists():
            gguf_files = list(model_dir.glob('*.gguf'))
            if gguf_files:
                print(f"   ✅ Found {len(gguf_files)} GGUF model(s) in {model_dir}")
                for model_file in gguf_files[:3]:  # Show first 3
                    print(f"      - {model_file.name}")
                    found_models.append(model_file)
                if len(gguf_files) > 3:
                    print(f"      ... and {len(gguf_files) - 3} more")

    if not found_models:
        print("   ⚠️  No GGUF models found")
        print("\n📥 Download GGUF models from Hugging Face:")
        print("   - Llama 3.2 3B: https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF")
        print("   - Mistral 7B: https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF")
        print("\n   Save to: C:\\Users\\tsmit\\models\\")

    return found_models


def check_registry():
    """Check model registry configuration."""
    print("\n🔍 Checking model registry...")

    registry_path = Path(__file__).parent.parent / 'realai' / 'models' / 'registry.json'

    if not registry_path.exists():
        print(f"   ❌ Registry not found: {registry_path}")
        return False

    try:
        with open(registry_path, 'r') as f:
            registry = json.load(f)

        llama_cli_models = [
            name for name, config in registry.items()
            if config.get('backend') in ['llama-cli', 'llama.cpp']
        ]

        if llama_cli_models:
            print(f"   ✅ Found {len(llama_cli_models)} llama-cli model(s) configured:")
            for model_name in llama_cli_models:
                config = registry[model_name]
                model_path = Path(config.get('path', ''))
                exists = '✅' if model_path.exists() else '❌'
                print(f"      {exists} {model_name}: {config.get('path')}")
        else:
            print("   ⚠️  No llama-cli models configured in registry")
            print("\n   Add a model to realai/models/registry.json:")
            print("""
   {
     "llama-local": {
       "type": "chat",
       "backend": "llama-cli",
       "path": "C:/Users/tsmit/models/llama-3.2-3b-instruct.Q4_K_M.gguf",
       "context_length": 8192
     }
   }
            """)

        return len(llama_cli_models) > 0

    except Exception as exc:
        print(f"   ❌ Error reading registry: {exc}")
        return False


def check_dependencies():
    """Check Python dependencies."""
    print("\n🔍 Checking Python dependencies...")

    required = ['fastapi', 'uvicorn', 'requests']
    missing = []

    for package in required:
        try:
            __import__(package)
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package}")
            missing.append(package)

    if missing:
        print(f"\n📦 Install missing packages:")
        print(f"   pip install {' '.join(missing)}")
        return False

    return True


def test_server():
    """Test if server can start."""
    print("\n🚀 Testing server startup...")

    try:
        import requests
        from realai.server.app import app

        print("   ✅ Server modules loaded successfully")

        # Try to import backends
        try:
            from realai.server.backends import RESOLVER
            from realai.server.llama_cli_backend import LlamaCliBackend

            backend = LlamaCliBackend()
            if backend.available():
                print("   ✅ llama-cli backend is available")
            else:
                print("   ⚠️  llama-cli backend not available (but server will work)")
        except Exception as exc:
            print(f"   ⚠️  Backend check failed: {exc}")

        print("\n✅ Server is ready to start!")
        print("\n🎯 Start the server with:")
        print("   python -m realai.server.app")
        print("   # or")
        print("   uvicorn realai.server.app:app --host 127.0.0.1 --port 8000")

        return True

    except Exception as exc:
        print(f"   ❌ Server check failed: {exc}")
        return False


def main():
    """Run all checks."""
    print("=" * 70)
    print("RealAI Local Llama.cpp Setup Checker")
    print("=" * 70)

    checks = {
        'llama-cli': check_llama_cli(),
        'models': check_gguf_models(),
        'registry': check_registry(),
        'dependencies': check_dependencies(),
        'server': False,
    }

    # Only test server if dependencies are met
    if checks['dependencies']:
        checks['server'] = test_server()

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    print(f"✅ llama-cli available: {bool(checks['llama-cli'])}")
    print(f"✅ GGUF models found: {len(checks['models']) if checks['models'] else 0}")
    print(f"✅ Registry configured: {checks['registry']}")
    print(f"✅ Dependencies installed: {checks['dependencies']}")
    print(f"✅ Server ready: {checks['server']}")

    all_ready = (
        checks['llama-cli'] and
        checks['models'] and
        checks['registry'] and
        checks['dependencies'] and
        checks['server']
    )

    if all_ready:
        print("\n🎉 All checks passed! You're ready to run RealAI locally.")
        print("\n📖 See docs/local-llama-setup.md for complete documentation.")
        return 0
    else:
        print("\n⚠️  Some checks failed. Review the output above for next steps.")
        print("\n📖 See docs/local-llama-setup.md for setup instructions.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
