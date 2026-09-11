"""Quick-start script for RealAI-clean local llama.cpp / Vulkan inference.

Verifies llama-server, repo GGUFs, and model catalog/registry for this tree.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_MODELS = _ROOT / "models"
_DEFAULT_GGUF = _MODELS / "qwen2.5-coder-7b-instruct-q5_k_m.gguf"


def check_llama_cli():
    """Check if llama-server / llama-cli is available (Vulkan preferred)."""
    print("Checking for llama-server / llama-cli...")

    for name in ("llama-server", "llama-server.exe", "llama-cli", "llama-cli.exe"):
        found = shutil.which(name)
        if found:
            print(f"   Found in PATH: {found}")
            return Path(found)

    common_paths = [
        Path("C:/llama-vulkan/llama-server.exe"),
        Path.home() / "llama.cpp" / "build" / "bin" / "Release" / "llama-server.exe",
        Path.home() / "llama.cpp" / "build" / "bin" / "Release" / "llama-cli.exe",
        Path("C:/llama.cpp/build/bin/Release/llama-server.exe"),
        Path("C:/llama.cpp/build/bin/Release/llama-cli.exe"),
        Path("C:/llama.cpp/llama-cli.exe"),
    ]

    for path in common_paths:
        if path.exists():
            print(f"   Found: {path}")
            return path

    print("   llama-server/cli not found")
    print("   Prefer: C:\\llama-vulkan\\llama-server.exe (Vulkan)")
    print("   Or: https://github.com/ggerganov/llama.cpp/releases")
    return None


def check_gguf_models():
    """Check for GGUF models (repo models/ first)."""
    print("\nChecking for GGUF models...")

    common_dirs = [
        _MODELS,
        Path.cwd() / "models",
        Path.home() / "models",
        Path("C:/Users/tsmit/models"),
    ]

    found_models = []
    seen = set()
    for model_dir in common_dirs:
        if not model_dir.exists():
            continue
        gguf_files = sorted(model_dir.glob("*.gguf"))
        if not gguf_files:
            continue
        print(f"   Found {len(gguf_files)} GGUF model(s) in {model_dir}")
        for model_file in gguf_files:
            key = model_file.name.lower()
            if key in seen:
                continue
            seen.add(key)
            print(f"      - {model_file.name}")
            found_models.append(model_file)

    if _DEFAULT_GGUF.is_file():
        print(f"   Default coder GGUF OK: {_DEFAULT_GGUF.name}")
    else:
        print(f"   Default coder GGUF missing: {_DEFAULT_GGUF}")

    if not found_models:
        print("   No GGUF models found")
        print("   Place files under: C:\\models\\checkpoints_lora\\")
        print("   Expected default: qwen2.5-coder-7b-instruct-q5_k_m.gguf")

    return found_models


def check_registry():
    """Check model catalog + legacy registries."""
    print("\nChecking model registry / catalog...")

    ok_any = False
    catalog_cfg = _ROOT / "config" / "realai_models.json"
    if catalog_cfg.is_file():
        try:
            data = json.loads(catalog_cfg.read_text(encoding="utf-8"))
            models = data.get("models") or []
            print(f"   config/realai_models.json: {len(models)} model id(s)")
            for m in models[:8]:
                mid = m.get("id")
                fn = m.get("gguf_filename") or "(no gguf)"
                local = (_MODELS / fn) if m.get("gguf_filename") else None
                mark = "OK" if local and local.is_file() else ("n/a" if not m.get("gguf_filename") else "missing")
                print(f"      [{mark}] {mid} -> {fn}")
            ok_any = len(models) > 0
        except Exception as exc:
            print(f"   Error reading realai_models.json: {exc}")
    else:
        print(f"   config/realai_models.json not found (will seed from models/*.gguf)")

    # Live catalog import
    try:
        sys.path.insert(0, str(_ROOT))
        from realai import model_catalog
        cat = model_catalog.build_catalog()
        ids = [m.get("id") for m in (cat.get("data") or cat.get("models") or [])]
        if not ids and isinstance(cat.get("models"), list):
            ids = [m.get("id") for m in cat["models"]]
        # build_catalog returns dict with models list in OpenAI shape under data sometimes
        if not ids:
            # facade shape: {"object":"list","data":[...]} or raw models
            data = cat.get("data") if isinstance(cat, dict) else None
            if data is None and isinstance(cat, dict):
                data = cat.get("models")
            if isinstance(data, list):
                ids = [m.get("id") for m in data if isinstance(m, dict)]
        print(f"   model_catalog.build_catalog(): {len(ids)} id(s)")
        for i in ids[:10]:
            print(f"      - {i}")
        ok_any = ok_any or bool(ids)
    except Exception as exc:
        print(f"   model_catalog import failed: {exc}")

    registry_path = _ROOT / "realai" / "models" / "registry.json"
    if registry_path.exists():
        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            local_models = [
                name
                for name, config in registry.items()
                if isinstance(config, dict)
                and config.get("backend") in ("llama-cli", "llama.cpp", "llama.cpp-vulkan")
            ]
            if local_models:
                print(f"   realai/models/registry.json local backends: {len(local_models)}")
                for model_name in local_models:
                    config = registry[model_name]
                    model_path = Path(config.get("path", ""))
                    if not model_path.is_file() and config.get("path"):
                        alt = _MODELS / Path(str(config.get("path"))).name
                        model_path = alt if alt.is_file() else model_path
                    exists = "OK" if model_path.exists() else "missing"
                    print(f"      [{exists}] {model_name}: {config.get('path')}")
                ok_any = True
        except Exception as exc:
            print(f"   Error reading registry.json: {exc}")

    return ok_any


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

        print("\nServer modules OK.")
        print("\nPreferred local chat stack:")
        print("   start_gpu_chat.bat")
        print("   powershell -File scripts\\run_local_chat.ps1")
        print("Legacy API app:")
        print("   python -m realai.server.app")
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
