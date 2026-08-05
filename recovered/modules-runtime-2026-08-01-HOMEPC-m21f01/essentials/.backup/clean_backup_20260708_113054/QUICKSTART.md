# Quick Start Guide

Get started with RealAI in under 5 minutes!

## Step 1: Installation

Clone and install:

```bash
git clone https://github.com/Unwrenchable/realai.git
cd realai
pip install -e .   # -e = editable/development mode; the dot (.) means "install from the current directory"
```

## Step 2: Run Examples

Try the built-in examples:

```bash
python examples.py
```

This demonstrates 9 core capabilities in a quick-start flow.

## Step 3: Use in Your Code

Create a new Python file:

```python
from realai import RealAIClient

# Initialize client
client = RealAIClient()

# Use chat completion
response = client.chat.create(
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Explain quantum computing in simple terms."}
    ]
)

print(response['choices'][0]['message']['content'])

# Generate a short video
video = client.videos.generate(
    prompt="A smooth drone shot over a tropical beach",
    duration=4
)
print(video['data'][0]['url'])
```

## Step 4: Launch the GUI — One .exe, Everything Included

> **"Why so many files in the repo?"**  
> The `.py` files are just source code.  You only need **one** output file
> (`RealAI.exe`) to run the whole application.  Build it once, share it freely.

### Run directly (no build step)

```bash
python realai_gui.py
```

### Build a single Windows .exe

Run these commands from inside the repository directory (e.g. `cd realai`):

```bash
pip install pyinstaller
pyinstaller realai_launcher.spec
# Output: dist\RealAI.exe  ← this one file is all you need
```

The `.exe` bundles the GUI, the API server, and the core RealAI module —
nothing else needs to be installed on the target machine.

## Step 5: Start the API Server and Use the Built-in Chat

### Via the GUI (easiest)

1. Open `RealAI.exe` (or run `python realai_gui.py`).
2. Enter at least one provider API key, then click **Save Keys**.
3. Click **🚀 Start API Server** — the status bar shows `http://localhost:8000`.
4. Type a message in the **Chat** panel at the bottom and press **Enter** (or click **➤ Send**).  
   The built-in chat sends your messages to the local server and displays the AI response — no browser or extra tools needed.

### Via the command line (headless / server machines)

```bash
# Set your provider key
export REALAI_OPENAI_API_KEY=sk-...

# Start the server
python -m realai.api_server
# or (legacy, still works)
python api_server.py
```

Then test with curl:

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### Connect a third-party UI

Any OpenAI-compatible front-end can point at the local server:

- **Base URL**: `http://localhost:8000/v1`
- **Model**: `realai-2.0`

## Step 6: Run Tests

Verify everything works:

```bash
python test_realai.py
```

## What Can You Do?

This quick-start walkthrough covers 9 core capabilities:

1. **Chat** - Conversational AI
2. **Text** - Text generation and completion
3. **Images** - Generate and analyze images
4. **Videos** - Generate videos from text or an input image
5. **Code** - Generate and understand code
6. **Embeddings** - Semantic text vectors
7. **Audio** - Transcribe and generate audio
8. **Translation** - Multilingual translation
9. **Analysis** - Image and content understanding

## Learn More

- See [README.md](README.md) for overview
- See [API.md](API.md) for detailed API documentation
- See [examples.py](examples.py) for code examples

## Need Help?

Open an issue on [GitHub](https://github.com/Unwrenchable/realai/issues)

---

**RealAI** - The AI model that can do it all! 🚀
