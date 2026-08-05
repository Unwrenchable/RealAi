"""Quick test script for the local server"""
import requests
import json

def test_health():
    response = requests.get("http://127.0.0.1:8000/health")
    print(f"Health check: {response.json()}")
    return response.status_code == 200

def test_models():
    response = requests.get("http://127.0.0.1:8000/v1/models")
    print(f"Models: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_chat():
    payload = {
        "model": "llama-3.2-1b",
        "messages": [
            {"role": "user", "content": "Say hello in one sentence."}
        ],
        "max_tokens": 50
    }

    print("\nSending chat request...")
    response = requests.post(
        "http://127.0.0.1:8000/v1/chat/completions",
        json=payload
    )

    if response.status_code == 200:
        result = response.json()
        print(f"\nResponse: {json.dumps(result, indent=2)}")
        print(f"\nGenerated text: {result['choices'][0]['message']['content']}")
        return True
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return False

if __name__ == "__main__":
    print("Testing RealAI Local Server...\n")

    if test_health():
        print("✓ Health check passed\n")

    if test_models():
        print("✓ Models list passed\n")

    if test_chat():
        print("\n✓ Chat completion passed!")
    else:
        print("\n✗ Chat completion failed")
