# RealAI API Documentation

## Overview

RealAI provides a comprehensive, OpenAI-compatible API for various AI capabilities. This document describes all available endpoints and methods.

## Table of Contents

- [Installation](#installation)
- [Basic Usage](#basic-usage)
- [API Methods](#api-methods)
  - [Chat Completions](#chat-completions)
  - [Text Completions](#text-completions)
  - [Image Generation](#image-generation)
  - [Video Generation](#video-generation)
  - [Image Analysis](#image-analysis)
  - [Code Generation](#code-generation)
  - [Embeddings](#embeddings)
  - [Audio Transcription](#audio-transcription)
  - [Audio Generation](#audio-generation)
  - [Translation](#translation)
  - [Chain-of-Thought Reasoning](#chain-of-thought-reasoning)
  - [Knowledge Synthesis](#knowledge-synthesis)
  - [Self-Reflection](#self-reflection)
  - [Multi-Agent Orchestration](#multi-agent-orchestration)
- [REST API Server](#rest-api-server)

## Installation

```bash
pip install git+https://github.com/Unwrenchable/realai.git
```

Or from source:

```bash
git clone https://github.com/Unwrenchable/realai.git
cd realai
pip install -e .   # -e = editable/development mode; the dot (.) means "install from the current directory"
```

## Basic Usage

```python
from realai import RealAIClient

# Initialize the client
client = RealAIClient(api_key="optional-api-key")

# Use any of the available methods
response = client.chat.create(
    messages=[{"role": "user", "content": "Hello!"}]
)
```

## API Methods

### Chat Completions

Create a conversational response (like ChatGPT).

**Method:** `client.chat.create(**kwargs)`

**Parameters:**
- `messages` (List[Dict[str, str]], required): List of messages with 'role' and 'content'
- `temperature` (float, optional): Sampling temperature (0-2), default: 0.7
- `max_tokens` (int, optional): Maximum tokens to generate
- `stream` (bool, optional): Whether to stream the response, default: False

**Example:**
```python
response = client.chat.create(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What can you do?"}
    ],
    temperature=0.7,
    max_tokens=150
)
```

**Response:**
```json
{
  "id": "chatcmpl-1234567890",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "realai-2.0",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "I am RealAI..."
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "total_tokens": 30
  }
}
```

### Text Completions

Generate text completions (like GPT-3).

**Method:** `client.completions.create(**kwargs)`

**Parameters:**
- `prompt` (str, required): The text prompt
- `temperature` (float, optional): Sampling temperature (0-2), default: 0.7
- `max_tokens` (int, optional): Maximum tokens to generate

**Example:**
```python
response = client.completions.create(
    prompt="The future of AI is",
    temperature=0.8,
    max_tokens=100
)
```

### Image Generation

Generate images from text descriptions (like DALL-E).

**Method:** `client.images.generate(**kwargs)`

**Parameters:**
- `prompt` (str, required): The image description
- `size` (str, optional): Image size, default: "1024x1024"
- `quality` (str, optional): Image quality ("standard" or "hd"), default: "standard"
- `n` (int, optional): Number of images to generate, default: 1

**Example:**
```python
response = client.images.generate(
    prompt="A beautiful sunset over mountains",
    size="1024x1024",
    quality="hd",
    n=2
)
```

### Image Analysis

Analyze and describe images (like GPT-4 Vision).

**Method:** `client.images.analyze(**kwargs)`

**Parameters:**
- `image_url` (str, required): URL of the image to analyze
- `prompt` (str, optional): Question about the image

**Example:**
```python
response = client.images.analyze(
    image_url="https://example.com/image.jpg",
    prompt="What's in this image?"
)
```

### Video Generation

Generate videos from text prompts or from an input image.

**Method:** `client.videos.generate(**kwargs)`

**Parameters:**
- `prompt` (str, required): Video description
- `image_url` (str, optional): Source image URL for image-to-video generation
- `size` (str, optional): Video dimensions, default: `"1280x720"`
- `duration` (int, optional): Duration in seconds, default: `5`
- `fps` (int, optional): Frames per second, default: `24`
- `n` (int, optional): Number of videos to generate, default: `1`
- `response_format` (str, optional): `"url"` or `"b64_json"`, default: `"url"`

**Example:**
```python
response = client.videos.generate(
    prompt="A cinematic timelapse of a modern city at dusk",
    duration=5,
    size="1280x720",
    n=1
)
```

### Code Generation

Generate code from descriptions (like Codex).

**Method:** `client.model.generate_code(**kwargs)`

**Parameters:**
- `prompt` (str, required): Description of the code to generate
- `language` (str, optional): Programming language
- `context` (str, optional): Additional context or existing code

**Example:**
```python
response = client.model.generate_code(
    prompt="Create a function to calculate factorial",
    language="python"
)
```

### Embeddings

Create semantic text embeddings.

**Method:** `client.embeddings.create(**kwargs)`

**Parameters:**
- `input_text` (Union[str, List[str]], required): Text or list of texts to embed
- `model` (str, optional): Embedding model to use, default: "realai-embeddings"

**Example:**
```python
response = client.embeddings.create(
    input_text=["Hello world", "AI is amazing"]
)
```

### Audio Transcription

Transcribe audio to text (like Whisper).

**Method:** `client.audio.transcribe(**kwargs)`

**Parameters:**
- `audio_file` (str, required): Path or URL to audio file
- `language` (str, optional): Language of the audio
- `prompt` (str, optional): Optional prompt to guide the model

**Example:**
```python
response = client.audio.transcribe(
    audio_file="recording.mp3",
    language="en"
)
```

### Audio Generation

Generate audio from text (text-to-speech).

**Method:** `client.audio.generate(**kwargs)`

**Parameters:**
- `text` (str, required): Text to convert to speech
- `voice` (str, optional): Voice to use, default: "alloy"
- `model` (str, optional): TTS model to use, default: "realai-tts"

**Example:**
```python
response = client.audio.generate(
    text="Hello from RealAI!",
    voice="alloy"
)
```

### Translation

Translate text between languages.

**Method:** `client.model.translate(**kwargs)`

**Parameters:**
- `text` (str, required): Text to translate
- `target_language` (str, required): Target language code (e.g., 'es', 'fr', 'de')
- `source_language` (str, optional): Source language (auto-detected if not provided)

**Example:**
```python
response = client.model.translate(
    text="Hello, how are you?",
    target_language="es"
)
```

### Chain-of-Thought Reasoning

Solve a complex problem with explicit, step-by-step reasoning.

**Method:** `client.reasoning.solve(problem, domain=None)` or `client.reasoning.chain(problem, domain=None)`

**Parameters:**
- `problem` (str, required): The question or problem to reason through
- `domain` (str, optional): Domain hint — e.g. `"math"`, `"logic"`, `"science"`

**Example:**
```python
result = client.reasoning.solve(
    problem="If all mammals breathe air, and whales are mammals, do whales breathe air?",
    domain="logic"
)
print(result['steps'])    # list of reasoning steps
print(result['answer'])   # final conclusion
print(result['confidence'])
```

### Knowledge Synthesis

Combine research from multiple topics into unified cross-domain insights.

**Method:** `client.synthesis.combine(topics, output_format="narrative")` or `client.synthesis.cross_domain(topics, output_format="narrative")`

**Parameters:**
- `topics` (List[str], required): List of topics to synthesize (1–10)
- `output_format` (str, optional): `"narrative"` (default) or `"bullets"`

**Example:**
```python
result = client.synthesis.combine(
    topics=["artificial intelligence", "neuroscience", "ethics"],
    output_format="bullets"
)
print(result['synthesis'])    # unified insight text
print(result['connections'])  # list of cross-domain links
```

### Self-Reflection

Analyse past interactions and surface targeted improvement recommendations.

**Method:** `client.reflection.analyze(interaction_history=None, focus="general")` or `client.reflection.improve(focus)`

**Parameters:**
- `interaction_history` (List[Dict], optional): List of `{"role": ..., "content": ...}` messages
- `focus` (str, optional): `"general"` (default), `"accuracy"`, `"empathy"`, `"efficiency"`

**Example:**
```python
history = [
    {"role": "user", "content": "Summarize climate change."},
    {"role": "assistant", "content": "Climate change refers to ..."},
]
result = client.reflection.analyze(interaction_history=history, focus="accuracy")
print(result['strengths'])    # list of strengths identified
print(result['weaknesses'])   # list of weaknesses
print(result['improvements']) # actionable improvement suggestions
print(result['score'])        # overall quality score 0-1
```

### Multi-Agent Orchestration

Coordinate multiple specialised AI agents (planner, researcher, critic, synthesizer) to tackle a complex task.

**Method:** `client.agents.run(task, agent_roles=None)` or `client.agents.coordinate(task, roles=None)`

**Parameters:**
- `task` (str, required): High-level task description
- `agent_roles` (List[str], optional): Specialist roles to engage. Defaults to `["planner", "researcher", "critic", "synthesizer"]`. Available roles: `planner`, `researcher`, `analyst`, `critic`, `writer`, `synthesizer`

**Example:**
```python
result = client.agents.run(
    task="Evaluate the pros and cons of remote work",
    agent_roles=["researcher", "analyst", "critic"]
)
print(result['agent_results'])  # dict of role -> agent output
print(result['final_output'])   # coordinator-synthesised answer
```

## REST API Server

RealAI includes a built-in HTTP server that provides an OpenAI-compatible REST API.

```bash
python api_server.py
```

The server will start on `http://0.0.0.0:8000` by default.

### Available Endpoints

#### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "model": "realai-2.0"
}
```

#### GET /v1/models
List available models.

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "realai-2.0",
      "object": "model",
      "created": 1708308000,
      "owned_by": "realai"
    }
  ]
}
```

#### GET /v1/capabilities
Return the canonical capability catalog grouped by domain.

#### GET /v1/providers/capabilities?provider=<name>
Return capability support/limitations for a provider.

#### POST /v1/chat/completions
Create a chat completion.

**Request Body:**
```json
{
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "temperature": 0.7,
  "max_tokens": 150
}
```

All core generation/research endpoints include a `realai_meta` object in the
response with canonical contract metadata (capability, modality, provider,
model, timestamp, and contract version).

#### POST /v1/completions
Create a text completion.

**Request Body:**
```json
{
  "prompt": "Once upon a time",
  "temperature": 0.7,
  "max_tokens": 100
}
```

#### POST /v1/images/generations
Generate an image.

**Request Body:**
```json
{
  "prompt": "A beautiful sunset",
  "size": "1024x1024",
  "quality": "hd",
  "n": 1
}
```

#### POST /v1/videos/generations
Generate a video.

**Request Body:**
```json
{
  "prompt": "A cinematic timelapse of a modern city at dusk",
  "image_url": "https://example.com/source-image.png",
  "size": "1280x720",
  "duration": 5,
  "fps": 24,
  "n": 1,
  "response_format": "url"
}
```

#### POST /v1/embeddings
Create embeddings.

**Request Body:**
```json
{
  "input": "Hello world",
  "model": "realai-embeddings"
}
```

#### POST /v1/audio/transcriptions
Transcribe audio.

**Request Body:**
```json
{
  "file": "audio.mp3",
  "language": "en"
}
```

#### POST /v1/audio/speech
Generate speech.

**Request Body:**
```json
{
  "input": "Hello from RealAI",
  "voice": "alloy"
}
```

#### POST /v1/reasoning/chain
Solve a problem with explicit chain-of-thought reasoning.

**Request Body:**
```json
{
  "problem": "If all mammals breathe air, and whales are mammals, do whales breathe air?",
  "domain": "logic"
}
```

#### POST /v1/synthesis/knowledge
Synthesise cross-domain knowledge from multiple topics.

**Request Body:**
```json
{
  "topics": ["artificial intelligence", "neuroscience", "psychology"],
  "output_format": "narrative"
}
```

#### POST /v1/reflection/analyze
Analyse interaction history and return self-improvement insights.

**Request Body:**
```json
{
  "interaction_history": [
    {"role": "user", "content": "What is 2+2?"},
    {"role": "assistant", "content": "4"}
  ],
  "focus": "accuracy"
}
```

#### POST /v1/agents/orchestrate
Coordinate multiple specialised AI agents to solve a complex task.

**Request Body:**
```json
{
  "task": "Evaluate the pros and cons of electric vehicles",
  "agent_roles": ["researcher", "analyst", "critic", "synthesizer"]
}
```

## Migration from OpenAI

RealAI is designed to be a drop-in replacement for OpenAI's client. Simply replace:

```python
# Old OpenAI code
from openai import OpenAI
client = OpenAI(api_key="...")

# New RealAI code
from realai import RealAIClient
client = RealAIClient(api_key="...")
```

The API structure and method calls remain the same!

## Plugin System (API)

Local plugins can be added by placing modules in the `plugins/` package. A plugin module should expose a callable `register(model, config: dict) -> dict` which attaches methods or state to the provided `RealAI` model instance and returns metadata. Example:

```python
def register(model, config: dict) -> dict:
  def sample_action(data=None):
    return {"ok": True, "received": data}

  setattr(model, "sample_action", sample_action)
  return {"name": "sample_plugin", "version": "0.1", "capabilities": ["sample_action"], "methods": ["sample_action"]}
```

Load plugins via `client.plugins.load(plugin_name="sample_plugin")` or discover and load all local plugins with `client.model.load_all_plugins()`.

## Examples

See [examples.py](examples.py) for comprehensive usage examples.

## Testing

Run the test suite:

```bash
python test_realai.py
```

## License

MIT License - See [LICENSE](LICENSE) file for details.
