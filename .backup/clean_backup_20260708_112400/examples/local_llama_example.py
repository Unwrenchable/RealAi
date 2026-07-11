"""Example script demonstrating RealAI local llama.cpp inference.

This script shows how to:
1. Start the RealAI local server
2. Send chat completion requests
3. Use local GGUF models without cloud APIs
"""

import requests
import time


def check_server_health(base_url='http://127.0.0.1:8000'):
    """Check if the RealAI server is running and healthy."""
    try:
        response = requests.get(f'{base_url}/health', timeout=5)
        response.raise_for_status()
        health_data = response.json()

        print("✅ Server is healthy!")
        print(f"   Provider: {health_data.get('provider')}")
        print(f"   Profile: {health_data.get('profile')}")
        print(f"   Available models: {', '.join(health_data.get('available_models', []))}")
        return True
    except requests.exceptions.ConnectionError:
        print("❌ Server is not running")
        print("\n📝 Start the server with:")
        print("   python -m realai.server.app")
        print("   # or")
        print("   uvicorn realai.server.app:app --host 127.0.0.1 --port 8000")
        return False
    except Exception as exc:
        print(f"❌ Health check failed: {exc}")
        return False


def list_models(base_url='http://127.0.0.1:8000'):
    """List all available models."""
    try:
        response = requests.get(f'{base_url}/v1/models', timeout=5)
        response.raise_for_status()
        models_data = response.json()

        models = models_data.get('data', [])
        print(f"\n📋 Available Models ({len(models)}):")

        for model in models:
            model_id = model.get('id')
            model_type = model.get('type', 'unknown')
            backend = model.get('backend', 'unknown')
            print(f"   • {model_id} ({model_type}, {backend})")

        return models
    except Exception as exc:
        print(f"❌ Failed to list models: {exc}")
        return []


def chat_completion(
    model='llama-local',
    message='What is the capital of France?',
    base_url='http://127.0.0.1:8000',
    temperature=0.7,
    max_tokens=512
):
    """Send a chat completion request to the local server."""
    try:
        print(f"\n💬 Sending chat request...")
        print(f"   Model: {model}")
        print(f"   Message: {message}")

        start_time = time.time()

        response = requests.post(
            f'{base_url}/v1/chat/completions',
            json={
                'model': model,
                'messages': [
                    {'role': 'user', 'content': message}
                ],
                'temperature': temperature,
                'max_tokens': max_tokens
            },
            timeout=300  # 5 minute timeout
        )
        response.raise_for_status()

        elapsed = time.time() - start_time
        result = response.json()

        assistant_message = result['choices'][0]['message']['content']
        backend_used = result.get('backend', 'unknown')

        print(f"\n✅ Response received in {elapsed:.2f}s")
        print(f"   Backend: {backend_used}")
        print(f"\n📝 Assistant: {assistant_message}")

        return result

    except requests.exceptions.Timeout:
        print("❌ Request timed out (model inference took too long)")
        return None
    except requests.exceptions.HTTPError as exc:
        print(f"❌ HTTP error: {exc}")
        if hasattr(exc.response, 'json'):
            try:
                error_data = exc.response.json()
                print(f"   Error details: {error_data}")
            except:
                pass
        return None
    except Exception as exc:
        print(f"❌ Request failed: {exc}")
        return None


def multi_turn_conversation(model='llama-local', base_url='http://127.0.0.1:8000'):
    """Demonstrate a multi-turn conversation."""
    print("\n🔄 Starting multi-turn conversation...")

    messages = [
        {'role': 'user', 'content': 'What is Python?'},
        {'role': 'assistant', 'content': ''},  # Will be filled by response
        {'role': 'user', 'content': 'What are its main use cases?'},
    ]

    try:
        # First turn
        response = requests.post(
            f'{base_url}/v1/chat/completions',
            json={
                'model': model,
                'messages': messages[:1],
                'temperature': 0.7,
                'max_tokens': 256
            },
            timeout=300
        )
        response.raise_for_status()

        first_response = response.json()['choices'][0]['message']['content']
        messages[1]['content'] = first_response

        print(f"\n👤 User: {messages[0]['content']}")
        print(f"🤖 Assistant: {first_response[:100]}...")

        # Second turn
        response = requests.post(
            f'{base_url}/v1/chat/completions',
            json={
                'model': model,
                'messages': messages,
                'temperature': 0.7,
                'max_tokens': 256
            },
            timeout=300
        )
        response.raise_for_status()

        second_response = response.json()['choices'][0]['message']['content']

        print(f"\n👤 User: {messages[2]['content']}")
        print(f"🤖 Assistant: {second_response[:100]}...")

        print("\n✅ Multi-turn conversation completed!")

    except Exception as exc:
        print(f"❌ Conversation failed: {exc}")


def benchmark_inference(model='llama-local', base_url='http://127.0.0.1:8000', iterations=3):
    """Benchmark inference speed."""
    print(f"\n⚡ Benchmarking {model} ({iterations} iterations)...")

    test_prompt = "What is artificial intelligence?"
    times = []

    for i in range(iterations):
        try:
            start = time.time()
            response = requests.post(
                f'{base_url}/v1/chat/completions',
                json={
                    'model': model,
                    'messages': [{'role': 'user', 'content': test_prompt}],
                    'temperature': 0.7,
                    'max_tokens': 128
                },
                timeout=300
            )
            response.raise_for_status()
            elapsed = time.time() - start
            times.append(elapsed)

            result = response.json()
            text = result['choices'][0]['message']['content']
            tokens = len(text.split())  # Rough token estimate
            tokens_per_sec = tokens / elapsed if elapsed > 0 else 0

            print(f"   Iteration {i+1}: {elapsed:.2f}s ({tokens} tokens, ~{tokens_per_sec:.1f} tok/s)")

        except Exception as exc:
            print(f"   Iteration {i+1} failed: {exc}")

    if times:
        avg_time = sum(times) / len(times)
        print(f"\n📊 Average inference time: {avg_time:.2f}s")


def main():
    """Run example demonstrations."""
    print("=" * 70)
    print("RealAI Local Llama.cpp Example")
    print("=" * 70)

    BASE_URL = 'http://127.0.0.1:8000'

    # Check server health
    if not check_server_health(BASE_URL):
        return 1

    # List available models
    models = list_models(BASE_URL)
    if not models:
        print("\n⚠️  No models available. Configure models in realai/models/registry.json")
        return 1

    # Find a local model (prefer llama-cli backend)
    local_model = None
    for model in models:
        if model.get('backend') in ['llama-cli', 'llama.cpp']:
            local_model = model.get('id')
            break

    if not local_model:
        print("\n⚠️  No local llama-cli models found. Using first available model.")
        local_model = models[0].get('id')

    print(f"\n🎯 Using model: {local_model}")

    # Example 1: Simple chat completion
    print("\n" + "=" * 70)
    print("Example 1: Simple Chat Completion")
    print("=" * 70)
    chat_completion(
        model=local_model,
        message="What is the capital of France?",
        base_url=BASE_URL
    )

    # Example 2: Technical question
    print("\n" + "=" * 70)
    print("Example 2: Technical Question")
    print("=" * 70)
    chat_completion(
        model=local_model,
        message="Explain what a RESTful API is in one paragraph.",
        base_url=BASE_URL,
        max_tokens=256
    )

    # Example 3: Multi-turn conversation
    print("\n" + "=" * 70)
    print("Example 3: Multi-turn Conversation")
    print("=" * 70)
    multi_turn_conversation(model=local_model, base_url=BASE_URL)

    # Example 4: Performance benchmark
    print("\n" + "=" * 70)
    print("Example 4: Performance Benchmark")
    print("=" * 70)
    benchmark_inference(model=local_model, base_url=BASE_URL, iterations=3)

    print("\n" + "=" * 70)
    print("✅ All examples completed!")
    print("=" * 70)
    print("\n📖 See docs/local-llama-setup.md for more information")

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
