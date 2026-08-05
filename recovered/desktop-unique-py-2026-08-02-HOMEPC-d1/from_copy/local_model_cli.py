#!/usr/bin/env python3
"""
RealAI Local Model Management CLI

Command-line tool for managing local AI models.
Usage:
    python local_model_cli.py list              # List all models
    python local_model_cli.py download <name>   # Download a model
    python local_model_cli.py test <name>       # Test a model
    python local_model_cli.py config            # Show configuration
    python local_model_cli.py set-default <name> # Set default model
"""

import sys
import argparse
from pathlib import Path

try:
    from local_models import (
        get_model_manager,
        get_llm_engine,
        LocalModelType
    )
except ImportError:
    from realai.local_models import (
        get_model_manager,
        get_llm_engine,
        LocalModelType
    )


def list_models(args):
    """List all configured models."""
    manager = get_model_manager()
    models = manager.list_models()

    if not models:
        print("No models configured.")
        print("\nTo get started with local models:")
        print("1. Install llama-cpp-python: pip install llama-cpp-python")
        print("2. Download a GGUF model from Hugging Face")
        print("3. Register it: python local_model_cli.py register <name> <path>")
        return

    print(f"Local Models ({len(models)} total):")
    print("-" * 80)

    for model in models:
        status = "✓ Available" if manager.is_model_available(model["name"]) else "✗ Not found"
        print(f"\n{model['name']} [{model['type']}] - {status}")
        if "path" in model:
            print(f"  Path: {model['path']}")
        if "backend" in model:
            print(f"  Backend: {model['backend']}")

    print("\n" + "-" * 80)
    default_llm = manager.config.get("default_llm")
    if default_llm:
        print(f"Default LLM: {default_llm}")
    else:
        print("No default LLM set. Use 'set-default' to configure one.")


def register_model(args):
    """Register a new local model."""
    manager = get_model_manager()

    model_path = Path(args.path).expanduser().resolve()
    if not model_path.exists():
        print(f"Error: Model file not found: {model_path}")
        return 1

    # Determine model type and backend from file extension
    suffix = model_path.suffix.lower()
    if suffix == ".gguf":
        backend = "llama-cpp"
        model_type = LocalModelType.LLM
    elif suffix in [".bin", ".pth", ".safetensors"]:
        backend = "transformers"
        model_type = LocalModelType.LLM
    else:
        print(f"Warning: Unknown model format '{suffix}'. Assuming GGUF/llama-cpp.")
        backend = "llama-cpp"
        model_type = LocalModelType.LLM

    config = {
        "path": str(model_path),
        "backend": backend,
        "context_length": args.context or 2048,
        "gpu_layers": args.gpu_layers if args.gpu_layers is not None else -1,
    }

    manager.register_model(args.name, model_type, config)
    print(f"✓ Registered model '{args.name}'")
    print(f"  Type: {model_type.value}")
    print(f"  Backend: {backend}")
    print(f"  Path: {model_path}")

    if not manager.config.get("default_llm"):
        print(f"\nSetting '{args.name}' as default LLM...")
        manager.config["default_llm"] = args.name
        manager._save_config()
        print("✓ Default LLM set")


def set_default(args):
    """Set the default model."""
    manager = get_model_manager()

    if not manager.is_model_available(args.name):
        print(f"Error: Model '{args.name}' not found or not available.")
        print("Use 'list' to see available models.")
        return 1

    model_info = manager.get_model_info(args.name)
    if model_info["type"] == LocalModelType.LLM.value:
        manager.config["default_llm"] = args.name
        manager._save_config()
        print(f"✓ Set default LLM to '{args.name}'")
    else:
        print(f"Error: Can only set LLM models as default (got {model_info['type']})")
        return 1


def test_model(args):
    """Test a model by generating text."""
    manager = get_model_manager()
    engine = get_llm_engine()

    if not manager.is_model_available(args.name):
        print(f"Error: Model '{args.name}' not found.")
        return 1

    print(f"Loading model '{args.name}'...")
    if not engine.load_model(args.name):
        print("✗ Failed to load model")
        return 1

    print("✓ Model loaded successfully")
    print("\nGenerating test response...")
    print("-" * 80)

    prompt = args.prompt or "Hello! How are you today?"
    print(f"Prompt: {prompt}\n")

    response = engine.generate(
        prompt,
        max_tokens=args.max_tokens or 100,
        temperature=0.7
    )

    print(f"Response: {response}")
    print("-" * 80)
    print("✓ Test completed successfully")


def show_config(args):
    """Show current configuration."""
    manager = get_model_manager()

    print("RealAI Local Models Configuration")
    print("=" * 80)
    print(f"\nModels directory: {manager.models_dir}")
    print(f"Config file: {manager.config_file}")

    print("\nPreferences:")
    prefs = manager.config.get("preferences", {})
    for key, value in prefs.items():
        print(f"  {key}: {value}")

    print(f"\nDefault LLM: {manager.config.get('default_llm', 'Not set')}")
    print(f"Default Embedding: {manager.config.get('default_embedding', 'Not set')}")

    print(f"\nTotal models: {len(manager.config.get('models', {}))}")


def download_model(args):
    """Download a recommended model."""
    print("Recommended Models for Local Inference:")
    print("=" * 80)
    print("\n1. Llama 3.2 1B (Fastest, low memory)")
    print("   huggingface-cli download bartowski/Llama-3.2-1B-Instruct-GGUF --include '*Q4_K_M.gguf'")
    print("\n2. Llama 3.2 3B (Good balance)")
    print("   huggingface-cli download bartowski/Llama-3.2-3B-Instruct-GGUF --include '*Q4_K_M.gguf'")
    print("\n3. Phi-3 Mini (Microsoft, 3.8B)")
    print("   huggingface-cli download microsoft/Phi-3-mini-4k-instruct-gguf --include '*q4.gguf'")
    print("\n4. Mistral 7B (High quality)")
    print("   huggingface-cli download TheBloke/Mistral-7B-Instruct-v0.2-GGUF --include '*Q4_K_M.gguf'")
    print("\n" + "=" * 80)
    print("\nTo download:")
    print("1. Install: pip install huggingface-hub")
    print("2. Run one of the commands above")
    print("3. Register the model: python local_model_cli.py register <name> <path-to-gguf>")
    print("\nExample:")
    print("  huggingface-cli download bartowski/Llama-3.2-1B-Instruct-GGUF --include '*Q4_K_M.gguf'")
    print("  python local_model_cli.py register llama3.2-1b ~/.cache/huggingface/hub/models--bartowski--Llama-3.2-1B-Instruct-GGUF/snapshots/.../Llama-3.2-1B-Instruct-Q4_K_M.gguf")


def main():
    parser = argparse.ArgumentParser(
        description="RealAI Local Model Management",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # List command
    subparsers.add_parser("list", help="List all configured models")

    # Register command
    register_parser = subparsers.add_parser("register", help="Register a new model")
    register_parser.add_argument("name", help="Name for the model")
    register_parser.add_argument("path", help="Path to model file")
    register_parser.add_argument("--context", type=int, help="Context length (default: 2048)")
    register_parser.add_argument("--gpu-layers", type=int, help="GPU layers (-1 for all, default: -1)")

    # Set default command
    default_parser = subparsers.add_parser("set-default", help="Set default model")
    default_parser.add_argument("name", help="Model name")

    # Test command
    test_parser = subparsers.add_parser("test", help="Test a model")
    test_parser.add_argument("name", help="Model name")
    test_parser.add_argument("--prompt", help="Test prompt")
    test_parser.add_argument("--max-tokens", type=int, help="Max tokens to generate")

    # Config command
    subparsers.add_parser("config", help="Show configuration")

    # Download command
    subparsers.add_parser("download", help="Show download instructions")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    commands = {
        "list": list_models,
        "register": register_model,
        "set-default": set_default,
        "test": test_model,
        "config": show_config,
        "download": download_model,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        return cmd_func(args) or 0
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
