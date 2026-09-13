"""
Example usage of RealAI model.

This script demonstrates how to use RealAI like OpenAI.
"""

from realai import RealAIClient
import json


def example_chat():
    """Example: Chat completion (like ChatGPT)."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Chat Completion (like ChatGPT)")
    print("="*60)
    
    client = RealAIClient()
    
    response = client.chat.create(
        messages=[
            {"role": "system", "content": "You are a helpful coding assistant."},
            {"role": "user", "content": "How do I reverse a string in Python?"}
        ],
        temperature=0.7,
        max_tokens=150
    )
    
    print(json.dumps(response, indent=2))


def example_text_completion():
    """Example: Text completion (like GPT-3)."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Text Completion (like GPT-3)")
    print("="*60)
    
    client = RealAIClient()
    
    response = client.completions.create(
        prompt="Once upon a time in a land far away",
        temperature=0.8,
        max_tokens=100
    )
    
    print(json.dumps(response, indent=2))


def example_image_generation():
    """Example: Image generation (like DALL-E)."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Image Generation (like DALL-E)")
    print("="*60)
    
    client = RealAIClient()
    
    response = client.images.generate(
        prompt="A futuristic city with flying cars at sunset",
        size="1024x1024",
        quality="hd",
        n=2
    )
    
    print(json.dumps(response, indent=2))


def example_image_analysis():
    """Example: Image analysis (like GPT-4 Vision)."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Image Analysis (like GPT-4 Vision)")
    print("="*60)
    
    client = RealAIClient()
    
    response = client.images.analyze(
        image_url="https://example.com/image.jpg",
        prompt="What objects are in this image?"
    )
    
    print(json.dumps(response, indent=2))


def example_code_generation():
    """Example: Code generation (like Codex)."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Code Generation (like Codex)")
    print("="*60)
    
    client = RealAIClient()
    
    response = client.model.generate_code(
        prompt="Create a binary search function",
        language="python"
    )
    
    print(json.dumps(response, indent=2))


def example_embeddings():
    """Example: Create embeddings."""
    print("\n" + "="*60)
    print("EXAMPLE 6: Text Embeddings")
    print("="*60)
    
    client = RealAIClient()
    
    response = client.embeddings.create(
        input_text=["Hello world", "RealAI is amazing"]
    )
    
    print(f"Generated {len(response['data'])} embeddings")
    print(f"Embedding dimension: {len(response['data'][0]['embedding'])}")


def example_audio_transcription():
    """Example: Audio transcription (like Whisper)."""
    print("\n" + "="*60)
    print("EXAMPLE 7: Audio Transcription (like Whisper)")
    print("="*60)
    
    client = RealAIClient()
    
    response = client.audio.transcribe(
        audio_file="audio.mp3",
        language="en"
    )
    
    print(json.dumps(response, indent=2))


def example_audio_generation():
    """Example: Audio generation (text-to-speech)."""
    print("\n" + "="*60)
    print("EXAMPLE 8: Audio Generation (Text-to-Speech)")
    print("="*60)
    
    client = RealAIClient()
    
    response = client.audio.generate(
        text="Hello, I am RealAI, the model that can do it all!",
        voice="alloy"
    )
    
    print(json.dumps(response, indent=2))


def example_translation():
    """Example: Translation."""
    print("\n" + "="*60)
    print("EXAMPLE 9: Translation")
    print("="*60)
    
    client = RealAIClient()
    
    response = client.model.translate(
        text="Hello, how are you?",
        target_language="es"
    )
    
    print(json.dumps(response, indent=2))


def example_model_info():
    """Example: Get model information and capabilities."""
    print("\n" + "="*60)
    print("EXAMPLE 10: Model Information & Capabilities")
    print("="*60)
    
    client = RealAIClient()
    
    info = client.model.get_model_info()
    print(json.dumps(info, indent=2))


if __name__ == "__main__":
    print("="*60)
    print("REALAI - THE AI MODEL THAT CAN DO IT ALL")
    print("OpenAI-Compatible Examples")
    print("="*60)
    
    # Run all examples
    example_model_info()
    example_chat()
    example_text_completion()
    example_image_generation()
    example_image_analysis()
    example_code_generation()
    example_embeddings()
    example_audio_transcription()
    example_audio_generation()
    example_translation()
    
    print("\n" + "="*60)
    print("All examples completed successfully!")
    print("="*60)
