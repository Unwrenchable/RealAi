#!/usr/bin/env python3
"""
RealAI Local AI Example

This example demonstrates how to use RealAI with your own local AI models
instead of external API providers. This gives you:
- Complete privacy (data never leaves your machine)
- Zero API costs
- No rate limits
- Full control and customization

Prerequisites:
1. Install llama-cpp-python: pip install llama-cpp-python
2. Download a model (see LOCAL_AI_GUIDE.md)
3. Register it: python local_model_cli.py register <name> <path>
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from realai import RealAIClient
    from local_models import get_model_manager, get_llm_engine
except ImportError:
    print("Error: Could not import RealAI modules")
    print("Make sure you're running this from the realai directory")
    sys.exit(1)


def check_setup():
    """Check if local models are set up."""
    manager = get_model_manager()
    models = manager.list_models()

    if not models:
        print("❌ No local models configured!")
        print("\nTo get started:")
        print("1. Install llama-cpp-python:")
        print("   pip install llama-cpp-python")
        print("\n2. Download a model:")
        print("   python local_model_cli.py download")
        print("\n3. Register it:")
        print("   python local_model_cli.py register <name> <path-to-model.gguf>")
        return False

    print(f"✓ Found {len(models)} local model(s)")
    default_llm = manager.config.get("default_llm")
    if default_llm:
        print(f"✓ Default model: {default_llm}")
    else:
        print("⚠ No default model set")
        print(f"  Set one with: python local_model_cli.py set-default {models[0]['name']}")
        return False

    return True


def example_basic_chat():
    """Example 1: Basic chat with local AI."""
    print("\n" + "="*80)
    print("Example 1: Basic Chat with Your Own AI")
    print("="*80)

    # Create client with local mode
    client = RealAIClient(provider="local")

    print("\nYou: Hello! Who are you?")

    response = client.chat.create(
        messages=[
            {"role": "user", "content": "Hello! Who are you?"}
        ]
    )

    print(f"AI: {response['choices'][0]['message']['content']}")
    print(f"\nModel used: {response.get('model', 'unknown')}")
    print(f"Source: {response.get('realai_meta', {}).get('source', 'unknown')}")


def example_text_completion():
    """Example 2: Text completion with local AI."""
    print("\n" + "="*80)
    print("Example 2: Text Completion")
    print("="*80)

    client = RealAIClient(provider="local")

    prompt = "The three laws of robotics are"
    print(f"\nPrompt: {prompt}")

    response = client.completions.create(
        prompt=prompt,
        max_tokens=150
    )

    print(f"Completion: {response['choices'][0]['text']}")
    print(f"\nModel used: {response.get('model', 'unknown')}")


def example_conversation():
    """Example 3: Multi-turn conversation."""
    print("\n" + "="*80)
    print("Example 3: Multi-turn Conversation")
    print("="*80)

    client = RealAIClient(provider="local")

    messages = [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": "What is Python?"}
    ]

    print("\nUser: What is Python?")
    response = client.chat.create(messages=messages)
    assistant_msg = response['choices'][0]['message']['content']
    print(f"AI: {assistant_msg}")

    # Continue the conversation
    messages.append({"role": "assistant", "content": assistant_msg})
    messages.append({"role": "user", "content": "Can you show me a simple example?"})

    print("\nUser: Can you show me a simple example?")
    response = client.chat.create(messages=messages)
    print(f"AI: {response['choices'][0]['message']['content']}")


def example_hybrid_mode():
    """Example 4: Hybrid mode - local first, API fallback."""
    print("\n" + "="*80)
    print("Example 4: Hybrid Mode (Local + API Fallback)")
    print("="*80)

    # Create client with both local and API support
    # It will use local models first, fall back to API if needed
    api_key = os.getenv("REALAI_OPENAI_API_KEY")

    if api_key:
        print("\n✓ API key found - hybrid mode enabled")
        client = RealAIClient(
            api_key=api_key,
            use_local=True  # Prefer local, but can fall back to API
        )
    else:
        print("\n⚠ No API key - using local only")
        client = RealAIClient(provider="local")

    response = client.chat.create(
        messages=[
            {"role": "user", "content": "Explain quantum entanglement briefly"}
        ]
    )

    print(f"\n{response['choices'][0]['message']['content']}")
    print(f"\nSource: {response.get('realai_meta', {}).get('source', 'unknown')}")


def example_model_info():
    """Example 5: Get model information."""
    print("\n" + "="*80)
    print("Example 5: Model Information")
    print("="*80)

    manager = get_model_manager()
    engine = get_llm_engine()

    print("\nConfigured Models:")
    models = manager.list_models()
    for model in models:
        available = "✓" if manager.is_model_available(model['name']) else "✗"
        print(f"  {available} {model['name']} ({model['type']})")
        if 'path' in model:
            print(f"     Path: {model['path']}")

    print("\nPreferences:")
    prefs = manager.config.get("preferences", {})
    for key, value in prefs.items():
        print(f"  {key}: {value}")

    print(f"\nModels directory: {manager.models_dir}")


def interactive_chat():
    """Example 6: Interactive chat session."""
    print("\n" + "="*80)
    print("Example 6: Interactive Chat (Your Own AI!)")
    print("="*80)
    print("\nType 'quit' to exit, 'clear' to clear history")

    client = RealAIClient(provider="local")
    messages = [
        {"role": "system", "content": "You are a helpful, friendly AI assistant."}
    ]

    print("\nYour own AI is ready! Start chatting:")
    print("-" * 80)

    while True:
        try:
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            if user_input.lower() == 'quit':
                print("\nGoodbye!")
                break

            if user_input.lower() == 'clear':
                messages = [messages[0]]  # Keep system message
                print("✓ Chat history cleared")
                continue

            messages.append({"role": "user", "content": user_input})

            response = client.chat.create(messages=messages, max_tokens=200)
            assistant_msg = response['choices'][0]['message']['content']

            print(f"\nAI: {assistant_msg}")

            messages.append({"role": "assistant", "content": assistant_msg})

        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")


def main():
    """Run all examples."""
    print("RealAI Local AI Examples")
    print("=" * 80)
    print("\n🎉 Welcome to YOUR OWN AI! 🎉")
    print("\nThese examples demonstrate RealAI running completely locally")
    print("with no external API dependencies. Your data stays private,")
    print("there are no API costs, and you have full control!")

    # Check setup
    if not check_setup():
        print("\n❌ Setup incomplete. Please follow the instructions above.")
        return 1

    # Run examples
    try:
        example_basic_chat()
        example_text_completion()
        example_conversation()
        example_hybrid_mode()
        example_model_info()

        # Ask if user wants interactive chat
        print("\n" + "="*80)
        response = input("\nWould you like to try interactive chat? (y/n): ").strip().lower()
        if response in ['y', 'yes']:
            interactive_chat()

    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print("\n" + "="*80)
    print("✓ Examples completed!")
    print("\n🚀 You're now running YOUR OWN AI - not a copy of another API!")
    print("Your AI is private, cost-free, and fully under your control.")
    print("\nNext steps:")
    print("- Try different models: python local_model_cli.py download")
    print("- Adjust settings: python local_model_cli.py config")
    print("- Build something amazing with your own AI!")

    return 0


if __name__ == "__main__":
    sys.exit(main())
