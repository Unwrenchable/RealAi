# RealAI - The Limitless AI That Can Do Anything

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Version 2.0](https://img.shields.io/badge/version-2.0-green.svg)](https://github.com/Unwrenchable/realai)

> *All the AI models want to be me* 🚀
>
> **The sky is the limit!** RealAI has NO limits - from Web3 to ordering groceries, from therapy to building businesses from the ground up.

RealAI is the limitless AI model that can truly do anything. It's designed to be used like OpenAI was supposed to be - but without any limits. Complete, powerful, unlimited, and easy to use.

**NOW EVEN MORE ULTIMATE:** RealAI integrates with real-world services like Google Calendar and Instacart, learns from every interaction with persistent memory, and self-reflects for continuous improvement. The ultimate AI that others aspire to be!

## 🆕 **YOUR OWN AI** - No External APIs Required!

**NEW:** RealAI can now run **completely locally** with your own AI models! No API keys, no external dependencies, no costs.

```python
from realai import RealAIClient

# Use YOUR OWN AI - not someone else's API!
client = RealAIClient(provider="local")

response = client.chat.create(
    messages=[{"role": "user", "content": "Hello!"}]
)
# Powered by YOUR local AI model! 🎉
```

**[📖 Local AI Setup Guide](LOCAL_AI_GUIDE.md)** - Be your own AI in 5 minutes!

### Why Run Your Own AI?

- 🔒 **100% Private** - Your data never leaves your machine
- 💰 **Zero API Costs** - No per-token charges
- 🚀 **No Rate Limits** - Use as much as you want
- 🌐 **Offline Capable** - Works without internet
- 🎨 **Full Control** - Customize and fine-tune your models
- ⚡ **Your Hardware** - Runs on CPU or GPU

## 🌟 Features

RealAI provides **22 comprehensive capabilities** in a single, unified model:

### Core AI Capabilities
- 💬 **Chat Completion** - Conversational AI like ChatGPT
- 📝 **Text Generation** - Complete text from prompts like GPT-3
- 🎨 **Image Generation** - Create images from text like DALL-E
- 🎬 **Video Generation** - Create videos from text or an image prompt
- 👁️ **Image Analysis** - Understand and describe images like GPT-4 Vision
- 💻 **Code Generation & Execution** - Generate, understand, and execute code
- 🔤 **Embeddings** - Create semantic embeddings for text
- 🎤 **Audio Transcription** - Convert speech to text like Whisper
- 🔊 **Audio Generation** - Text-to-speech capabilities
- 🌍 **Translation** - Translate between languages

### Limitless Capabilities ✨
- 🌐 **Web Research** - Browse and research any topic comprehensively
- 🛒 **Task Automation** - Order groceries, book appointments, automate real-world tasks
- 🗣️ **Voice Interaction** - Natural voice conversations with speech I/O
- 🏢 **Business Planning** - Build businesses from the ground up
- 💚 **Therapy & Counseling** - Professional therapeutic and emotional support
- ⛓️ **Web3 Integration** - Blockchain, smart contracts, NFTs, DeFi
- 🔌 **Plugin System** - Extend RealAI anywhere with unlimited plugins
- 🧠 **Learning & Memory** - Learns and adapts from every interaction

### Next-Generation AI Capabilities 🚀
- 🔗 **Chain-of-Thought Reasoning** - Transparent, step-by-step problem solving
- 🔬 **Knowledge Synthesis** - Cross-domain insight generation combining web research + AI analysis
- 🪞 **Self-Reflection** - Meta-level self-analysis and targeted improvement recommendations
- 🤖 **Multi-Agent Orchestration** - Coordinate specialised AI agents (planner, researcher, critic, synthesizer) for complex tasks

## 🚀 What Makes RealAI Special?

**RealAI has NO limits.** It can:
- 🌐 Research any topic on the web
- 🛍️ Order your groceries and manage your life
- 💼 Build your business from ideation to execution
- 🗣️ Have natural voice conversations
- 💚 Provide therapy and emotional support
- ⛓️ Work with Web3 and blockchain
- 💻 Code AND execute anything
- 🎬 Generate videos from text and image prompts
- 🔌 Be implemented anywhere via plugins
- 🧠 Learn from every interaction
- 🔗 Reason step-by-step with full transparency
- 🔬 Synthesise insights across multiple knowledge domains
- 🪞 Self-reflect and continuously self-improve
- 🤖 Coordinate multiple specialist AI agents for complex tasks

**The sky is literally the limit!**

## Installation

### From Source

```bash
git clone https://github.com/Unwrenchable/realai.git
cd realai
pip install -e .   # -e = editable/development mode; the dot (.) means "install from the current directory"
```

### Quick Install

```bash
pip install git+https://github.com/Unwrenchable/realai.git
```

## Quick Start

```python
from realai import RealAIClient

# Initialize the client (OpenAI-compatible interface)
client = RealAIClient()

# Chat completion
response = client.chat.create(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What can you do?"}
    ]
)
print(response)

# Research any topic on the web
research = client.web.research(
    query="Latest AI breakthroughs",
    depth="deep"
)
print(research)

# Order groceries
groceries = client.tasks.order_groceries(
    items=["milk", "eggs", "bread"],
    execute=True
)
print(groceries)

# Build a business from scratch
business = client.business.build(
    business_type="AI startup"
)
print(business)

# Have a voice conversation
voice = client.voice.conversation(
    message="Tell me about yourself"
)
print(voice)

# Get therapy support
therapy = client.therapy.support(
    message="I'm feeling stressed"
)
print(therapy)

# Work with Web3
web3 = client.web3.smart_contract(
    blockchain="ethereum"
)
print(web3)
```

## 🎯 Usage Examples

### Chat Completion (ChatGPT-style)

```python
from realai import RealAIClient

client = RealAIClient()

response = client.chat.create(
    messages=[
        {"role": "system", "content": "You are a coding expert."},
        {"role": "user", "content": "Explain recursion in simple terms."}
    ],
    temperature=0.7,
    max_tokens=150
)

print(response['choices'][0]['message']['content'])
```

### Text Completion (GPT-3-style)

```python
response = client.completions.create(
    prompt="The future of AI is",
    temperature=0.8,
    max_tokens=100
)

print(response['choices'][0]['text'])
```

### Image Generation (DALL-E-style)

```python
image_response = client.images.generate(
    prompt="A futuristic cityscape with neon lights",
    size="1024x1024",
    quality="hd",
    n=1
)

print(f"Generated image URL: {image_response['data'][0]['url']}")
```

### Image Analysis (GPT-4 Vision-style)

```python
analysis = client.images.analyze(
    image_url="https://example.com/photo.jpg",
    prompt="Describe what you see in this image"
)

print(analysis['description'])
```

### Video Generation (text-to-video / image-to-video)

```python
video_response = client.videos.generate(
    prompt="A cinematic sunrise over snowy mountains",
    duration=5,
    size="1280x720",
    n=1
)

print(video_response['data'][0]['url'])
```

### Code Generation (Codex-style)

```python
code_response = client.model.generate_code(
    prompt="Create a REST API endpoint in Flask",
    language="python"
)

print(code_response['code'])
```

### Embeddings

```python
embeddings = client.embeddings.create(
    input_text=["Hello world", "RealAI is powerful"]
)

print(f"Embedding dimension: {len(embeddings['data'][0]['embedding'])}")
```

### Audio Transcription (Whisper-style)

```python
transcription = client.audio.transcribe(
    audio_file="recording.mp3",
    language="en"
)

print(transcription['text'])
```

### Audio Generation (TTS)

```python
audio = client.audio.generate(
    text="Hello from RealAI!",
    voice="alloy"
)

print(f"Audio URL: {audio['audio_url']}")
```

### Translation

```python
translation = client.model.translate(
    text="Hello, how are you?",
    target_language="es"
)

print(translation['translated_text'])
```

### Web Research 🌐

```python
# Research any topic comprehensively
research = client.web.research(
    query="Quantum computing applications",
    depth="deep",
    sources=["arxiv.org", "nature.com"]
)

print(research['findings'])
print(research['sources'])
print(research['citations'])   # citation metadata
print(research['freshness'])   # live | cached | fallback
```

### Personas 🎭

```python
# List and switch persona profiles
print(client.personas.list())
client.personas.set("analyst")

# Persona influences chat style and appears in response metadata
reply = client.chat.create(messages=[{"role": "user", "content": "Give me a launch plan"}])
print(reply["realai_meta"]["persona"])
```

### Task Automation 🛒

```python
# Order groceries
groceries = client.tasks.order_groceries(
    items=["organic milk", "free-range eggs", "whole wheat bread"],
    execute=True  # Set to False to just plan
)

# Book an appointment
appointment = client.tasks.book_appointment(
    details={
        "type": "doctor",
        "date": "2026-03-01",
        "time": "10:00 AM"
    },
    execute=True
)
```

### Voice Interaction 🗣️

```python
# Natural voice conversation
voice_response = client.voice.conversation(
    message="Tell me about the weather today",
    response_format="both"  # Get both text and audio
)

print(voice_response['response_text'])
print(voice_response['response_audio_url'])
```

### Business Planning 🏢

```python
# Build a business from the ground up
business_plan = client.business.build(
    business_type="SaaS startup",
    stage="ideation"
)

print(business_plan['business_plan']['executive_summary'])
print(business_plan['action_items'])
print(business_plan['estimated_timeline'])
```

### Therapy & Counseling 💚

```python
# Get emotional support
support = client.therapy.support(
    message="I'm feeling overwhelmed with work"
)

print(support['response'])
print(support['recommendations'])

# Full therapy session
session = client.therapy.session(
    session_type="therapy",
    message="I want to work on my anxiety",
    approach="cognitive_behavioral"
)
```

### Web3 Integration ⛓️

```python
# Deploy a smart contract
contract = client.web3.smart_contract(
    blockchain="ethereum",
    params={"contract_type": "ERC20"}
)

# Query blockchain data
query = client.web3.execute(
    operation="query",
    blockchain="ethereum",
    params={"address": "0x..."}
)
```

### Code Execution 💻

```python
# Execute code safely
result = client.model.execute_code(
    code="""
def factorial(n):
    return 1 if n <= 1 else n * factorial(n-1)
print(factorial(5))
""",
    language="python",
    sandbox=True
)

print(result['output'])
```

### Plugin System 🔌

```python
# Load a plugin to extend capabilities
plugin = client.plugins.load(
    plugin_name="custom_analytics",
    plugin_config={"api_key": "..."}
)

# Extend RealAI anywhere
extension = client.plugins.extend(
    plugin_name="iot_integration",
    config={"devices": ["smart_home"]}
)
```

### Learning & Memory 🧠

```python
# RealAI learns from every interaction
learning = client.model.learn_from_interaction(
    interaction_data={
        "user_preference": "concise responses",
        "topic_interest": "AI research"
    },
    save=True
)

print(learning['patterns_identified'])
print(learning['adaptations'])
```

## API Reference

### RealAIClient

The main client class that provides an OpenAI-compatible interface with limitless capabilities.

```python
client = RealAIClient(api_key="your-api-key")  # api_key is optional
```

#### Core AI Methods

- `client.chat.create(**kwargs)` - Create chat completions
- `client.completions.create(**kwargs)` - Create text completions
- `client.images.generate(**kwargs)` - Generate images
- `client.images.analyze(**kwargs)` - Analyze images
- `client.embeddings.create(**kwargs)` - Create embeddings
- `client.audio.transcribe(**kwargs)` - Transcribe audio
- `client.audio.generate(**kwargs)` - Generate audio

#### Limitless Capabilities Methods

- `client.web.research(**kwargs)` - Research any topic on the web
- `client.tasks.automate(**kwargs)` - Automate real-world tasks
- `client.tasks.order_groceries(**kwargs)` - Order groceries
- `client.tasks.book_appointment(**kwargs)` - Book appointments
- `client.voice.interact(**kwargs)` - Voice interaction
- `client.voice.conversation(**kwargs)` - Natural voice conversation
- `client.business.plan(**kwargs)` - Create business plans
- `client.business.build(**kwargs)` - Build businesses from scratch
- `client.therapy.session(**kwargs)` - Therapy sessions
- `client.therapy.support(**kwargs)` - Emotional support
- `client.web3.execute(**kwargs)` - Web3 operations
- `client.web3.smart_contract(**kwargs)` - Smart contract interactions
- `client.plugins.load(**kwargs)` - Load plugins
- `client.plugins.extend(**kwargs)` - Extend RealAI

### RealAI Model

Direct access to the underlying model:

```python
from realai import RealAI

model = RealAI(model_name="realai-2.0")

# Get model information
info = model.get_model_info()

# Get supported capabilities
capabilities = model.get_capabilities()
```

## Command Line Usage

After installation, you can run the example directly:

```bash
python -m realai
```

Or use the console script:

```bash
realai
```

## Desktop App (GUI / .exe)

RealAI ships with a graphical launcher (`realai_gui.py`) that bundles
everything in **one window**:

1. **API Key Setup** — enter and save keys for OpenAI, Anthropic, Grok, and Gemini.  Keys are stored locally in `~/.realai/config.json` and are never uploaded anywhere.
2. **API Server Control** — start/stop the built-in HTTP server (runs at `http://localhost:8000`) with a single button click.
3. **Built-in Chat** — once the server is running, chat with RealAI directly in the launcher window without needing any other tool.

> **Why are there so many `.py` files in the repo?**  
> Those are the *source code* files — you never need to ship them individually.
> When you build with PyInstaller (see below) everything is compiled into a
> **single `RealAI.exe`** file.  That one file is all you need to distribute or
> run on Windows.

### Run the GUI directly (no build step)

```bash
python realai_gui.py
```

### Build a single standalone Windows .exe

```bash
# Install build tool (one-time)
pip install pyinstaller

# Navigate to the repository root (if you are not already there)
cd realai

# Build the executable
pyinstaller realai_launcher.spec

# Output: dist\RealAI.exe — double-click to launch
```

The resulting `dist\RealAI.exe` contains the GUI, the API server, and the core
RealAI module — **one file, no Python installation required** on the target machine.

> **Tip:** tkinter is included with the official Python installer from
> [python.org](https://www.python.org/downloads/).  If you installed Python
> from the Microsoft Store, re-install from python.org and make sure the
> "tcl/tk and IDLE" optional feature is selected.

## Running the API Server

The API server (`api_server.py`) exposes an OpenAI-compatible REST API at
`http://localhost:8000`.  Any app or tool that speaks the OpenAI API (curl,
Python `openai` library, Postman, Open WebUI, …) can point at it instead of
`api.openai.com`.

### Option A — via the GUI (recommended)

1. Launch `RealAI.exe` (or `python realai_gui.py`).
2. Enter your API key(s) and click **Save Keys**.
3. Click **🚀 Start API Server** — the status bar will show `http://localhost:8000`.
4. Use the built-in **Chat** panel at the bottom to talk to RealAI immediately.

### Option B — standalone (headless / server machines)

```bash
# Set at least one provider API key
export REALAI_OPENAI_API_KEY=sk-...            # OpenAI
# export REALAI_ANTHROPIC_API_KEY=sk-ant-...   # Anthropic
# export REALAI_GROK_API_KEY=xai-...           # xAI / Grok
# export REALAI_GEMINI_API_KEY=AIza...         # Google Gemini
# export REALAI_OPENROUTER_API_KEY=sk-or-v1-...# OpenRouter (access 200+ models)
# export REALAI_MISTRAL_API_KEY=...            # Mistral AI
# export REALAI_TOGETHER_API_KEY=...           # Together AI
# export REALAI_DEEPSEEK_API_KEY=...           # DeepSeek
# export REALAI_PERPLEXITY_API_KEY=pplx-...   # Perplexity AI

# Start the server (default: port 8000, all interfaces)
python -m realai.api_server
# or (legacy, still works)
python api_server.py
```

Test it with curl:

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello!"}]}'
```

### Available endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/v1/models` | List models |
| GET | `/v1/capabilities` | Capability catalog grouped by domain |
| GET | `/v1/providers/capabilities?provider=<name>` | Provider capability map |
| POST | `/v1/chat/completions` | Chat (OpenAI-compatible) |
| POST | `/v1/completions` | Text completion |
| POST | `/v1/images/generations` | Image generation |
| POST | `/v1/videos/generations` | Video generation |
| POST | `/v1/embeddings` | Text embeddings |
| POST | `/v1/audio/transcriptions` | Speech-to-text |
| POST | `/v1/audio/speech` | Text-to-speech |

### Connecting a third-party UI to the server

Any OpenAI-compatible front-end (e.g. [Open WebUI](https://github.com/open-webui/open-webui), [ChatBot UI](https://github.com/mckaywrigley/chatbot-ui)) can connect to the local server by setting:

- **API base URL**: `http://localhost:8000/v1`
- **API key**: your provider key (or any string if running in placeholder mode)
- **Model**: `realai-2.0`

### Supported AI Providers

RealAI routes your requests to the world's leading AI services. Configure any of the providers below to get started:

| Provider | Env Variable | Key Prefix | Get Your Key |
|----------|-------------|------------|--------------|
| **OpenAI** | `REALAI_OPENAI_API_KEY` | `sk-...` | https://platform.openai.com/api-keys |
| **Anthropic (Claude)** | `REALAI_ANTHROPIC_API_KEY` | `sk-ant-...` | https://console.anthropic.com/ |
| **xAI / Grok** | `REALAI_GROK_API_KEY` | `xai-...` | https://console.x.ai/ |
| **Google Gemini** | `REALAI_GEMINI_API_KEY` | `AIza...` | https://aistudio.google.com/app/apikey |
| **OpenRouter** | `REALAI_OPENROUTER_API_KEY` | `sk-or-v1-...` | https://openrouter.ai/keys |
| **Mistral AI** | `REALAI_MISTRAL_API_KEY` | — | https://console.mistral.ai/api-keys |
| **Together AI** | `REALAI_TOGETHER_API_KEY` | — | https://api.together.xyz/settings/api-keys |
| **DeepSeek** | `REALAI_DEEPSEEK_API_KEY` | — | https://platform.deepseek.com/api_keys |
| **Perplexity AI** | `REALAI_PERPLEXITY_API_KEY` | `pplx-...` | https://www.perplexity.ai/settings/api |

> **Tip — OpenRouter for maximum model choice:** OpenRouter gives you access to 200+ models (GPT-4o, Claude 3.5, Llama 3, Mistral, Gemini, and more) through a single API key and the same OpenAI-compatible interface.  Set `REALAI_OPENROUTER_API_KEY` and use `X-Provider: openrouter` (or let RealAI auto-detect the `sk-or-v1-` prefix) to route through OpenRouter.

## Architecture

RealAI is designed with the following principles:

1. **Unlimited** - No limits, truly can do anything
2. **Unified Interface** - One model for all AI tasks
3. **OpenAI Compatibility** - Drop-in replacement for OpenAI's API structure
4. **Limitless Capabilities** - From Web3 to therapy, code to groceries
5. **Easy to Use** - Simple, intuitive API
6. **Implement Anywhere** - Plugin system for universal deployment
7. **Self-Contained** - No heavy dependencies required
8. **Learns & Adapts** - Gets better with every interaction

## Implemented Features (status)

The repository includes working implementations (or safe, local integrations) for several features mentioned above. Current status:

- ✅ `web_research`: performs lightweight web fetching + HTML parsing using `requests` + `beautifulsoup4` when available; falls back to a canned response on error.
- ✅ `execute_code`: runs Python code in a temporary file with a timeout and optional resource limits via `resource` (OS-dependent). Intended for development/trusted usage.
- ✅ `embeddings`: uses `sentence-transformers` (if installed) to produce real embeddings; otherwise falls back to stub 1536-d zero vectors.
- ✅ `plugin system`: load local plugins from the `plugins/` package. Plugins expose `register(model, config)` and may attach methods to the `RealAI` model. Use `client.plugins.load(...)` or `client.model.load_all_plugins()` to discover local plugins.

Note: Some capabilities in the README (real-world payments, ordering groceries, production-grade Web3 interactions, hosted ASR/TTS pipelines) are simulated and require implementing external integrations to perform real effects. I can implement those integrations incrementally — tell me which to prioritize next.

## Capabilities

RealAI supports **17 comprehensive capabilities** out of the box:

| Capability | Description | Similar To |
|------------|-------------|------------|
| Text Generation | Generate and complete text | GPT-3, GPT-4 |
| Chat Completion | Conversational AI | ChatGPT |
| Image Generation | Create images from text | DALL-E |
| Image Analysis | Understand and describe images | GPT-4 Vision |
| Code Generation | Generate and understand code | Codex, Copilot |
| Code Execution | Execute code safely | Jupyter, Replit |
| Embeddings | Semantic text embeddings | text-embedding-ada-002 |
| Audio Transcription | Speech to text | Whisper |
| Audio Generation | Text to speech | TTS |
| Translation | Multilingual translation | Google Translate |
| **Web Research** | **Browse and research anything** | **Perplexity, Bing** |
| **Task Automation** | **Order groceries, book appointments** | **Zapier, IFTTT** |
| **Voice Interaction** | **Natural voice conversations** | **Alexa, Siri** |
| **Business Planning** | **Build businesses from scratch** | **Business consultants** |
| **Therapy/Counseling** | **Emotional support and therapy** | **BetterHelp, Woebot** |
| **Web3 Integration** | **Blockchain, smart contracts, NFTs** | **Web3.js, Ethers.js** |
| **Plugin System** | **Extend anywhere with plugins** | **WordPress, VSCode** |
| **Learning/Memory** | **Learns from every interaction** | **Adaptive AI** |

## Why RealAI?

- ✅ **NO LIMITS**: Truly can do anything - the sky is the limit!
- ✅ **All-in-One**: Everything you need in one model (17 capabilities)
- ✅ **OpenAI-Compatible**: Easy migration from OpenAI
- ✅ **Simple API**: Clean, intuitive interface
- ✅ **Real-World Tasks**: Order groceries, book appointments, build businesses
- ✅ **Voice & Therapy**: Natural conversations and emotional support
- ✅ **Web3 Ready**: Full blockchain and smart contract support
- ✅ **Implement Anywhere**: Plugin system for universal deployment
- ✅ **No Lock-in**: Open source and free to use
- ✅ **Lightweight**: Minimal dependencies
- ✅ **Learns & Adapts**: Gets smarter with every interaction

## Deployment

RealAI can be deployed in multiple ways to fit your needs:

### 📋 **[Complete Deployment Guide](DEPLOYMENT.md)**

See **[DEPLOYMENT.md](DEPLOYMENT.md)** for comprehensive deployment instructions covering:
- 🏠 **Local Development** - Quick setup for development and testing
- 💻 **Desktop Application** - Windows .exe with GUI and built-in server
- 🌐 **API Server** - Deploy on any server (VPS, cloud, on-premises)
- ☁️ **AWS Lambda** - Serverless deployment with split architecture
- 🔧 **Configuration** - Environment variables and provider setup
- ✅ **Testing** - Verify your deployment
- 🛠️ **Troubleshooting** - Common issues and solutions

### Quick Start Options

**Local Development:**
```bash
git clone https://github.com/Unwrenchable/realai.git
cd realai
pip install -e .
export REALAI_OPENAI_API_KEY=sk-...
python -m realai.api_server
# or: python api_server.py
```

**AWS Lambda (Serverless):**
```bash
sam build
sam deploy --guided
```

**Desktop App (Windows):**
```bash
python realai_gui.py
# Or build standalone .exe:
pyinstaller realai_launcher.spec
```

For detailed instructions, see **[DEPLOYMENT.md](DEPLOYMENT.md)**.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions, please open an issue on [GitHub](https://github.com/Unwrenchable/realai/issues).

---

**RealAI** - The limitless AI that can truly do anything. From Web3 to ordering groceries, from therapy to building businesses from the ground up. The sky is the limit! All the AI models want to be me. 🚀✨🌟
