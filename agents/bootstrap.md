# RealAI — Local Bootstrap Guide

Follow the steps below to get RealAI running locally for development.

> **No secrets in this file.** Set API keys via environment variables or
> through the GUI (`~/.realai/config.json`). Never commit real keys.

---

## Prerequisites

| Tool | Minimum version | Install hint |
|------|----------------|--------------|
| Python | 3.7 | https://python.org (3.11 or 3.12 recommended) |
| pip | 21+ | Bundled with Python |
| Git | any recent | https://git-scm.com |
| tkinter | stdlib | Included in official Python installer |

---

## 1 — Clone and install

```bash
git clone https://github.com/Unwrenchable/realai.git
cd realai

# Install all runtime dependencies
pip install -r requirements.txt

# Or install in editable mode for development (enables `python -m realai`)
pip install -e .
```

---

## 2 — Configure at least one AI provider

RealAI falls back to placeholder responses when no API key is configured.
To get real AI responses, export at least one provider key:

```bash
# Choose any one (or more) of these:
export REALAI_OPENAI_API_KEY="sk-proj-..."
export REALAI_ANTHROPIC_API_KEY="sk-ant-..."
export REALAI_GEMINI_API_KEY="AIza..."
export REALAI_GROK_API_KEY="xai-..."
export REALAI_OPENROUTER_API_KEY="sk-or-..."
export REALAI_MISTRAL_API_KEY="mis-..."
export REALAI_TOGETHER_API_KEY="tog-..."
export REALAI_DEEPSEEK_API_KEY="dsk-..."
export REALAI_PERPLEXITY_API_KEY="pplx-..."
```

On Windows use `set` instead of `export`.  
Alternatively, enter keys in the GUI and click **Save Keys**.

---

## 3 — Run the test suite

```bash
python test_realai.py
```

All 30 tests should pass. Tests run without any API keys (they exercise the
fallback/stub paths).

---

## 4 — Choose an interface

### A. Python library

```python
from realai import RealAIClient

client = RealAIClient(api_key="sk-proj-...")
response = client.chat.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response["choices"][0]["message"]["content"])
```

### B. Command-line demo

```bash
python -m realai
```

### C. REST API server (OpenAI-compatible)

```bash
python api_server.py
# Server starts on http://localhost:8000

# Test with curl:
curl http://localhost:8000/health
curl http://localhost:8000/v1/models
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk-proj-..." \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"Hi"}]}'
```

### D. Graphical user interface

```bash
python realai_gui.py
```

Enter your API keys, click **Save Keys**, then click **Start Server** to start
the REST API in the background. Use the built-in chat panel to test.

---

## 5 — Optional: enable audio capabilities

### Text-to-speech (pyttsx3)

Already installed via `requirements.txt`. Test with:

```python
from realai import RealAIClient
client = RealAIClient()
result = client.audio.generate(input="Hello world", voice="default")
```

### Speech-to-text (Vosk)

1. Download a Vosk model from https://alphacephei.com/vosk/models  
   (e.g. `vosk-model-small-en-us-0.15` for lightweight English ASR)
2. Extract the archive: `unzip vosk-model-small-en-us-0.15.zip`
3. Set the environment variable:

```bash
export VOSK_MODEL_PATH="/path/to/vosk-model-small-en-us-0.15"
```

---

## 6 — Optional: enable Web3 capabilities

Set an Ethereum-compatible RPC endpoint:

```bash
export WEB3_PROVIDER_URL="https://mainnet.infura.io/v3/YOUR_PROJECT_ID"
```

Web3 operations are **read-only by default** (balances, contract queries).
Transaction signing requires additional implementation.

---

## 7 — Optional: build a standalone Windows executable

Requires Windows + PyInstaller:

```bash
pip install pyinstaller
pyinstaller realai_launcher.spec
# Output: dist/RealAI.exe
```

---

## 8 — Writing and running examples

```bash
python examples.py            # Core capability examples
python examples_limitless.py  # Extended capability examples
```

---

## 9 — Writing a plugin

See `plugins/sample_plugin.py` for the plugin registration pattern:

```python
# plugins/my_plugin.py
def register(model):
    def my_feature(input_text, **kwargs):
        return {"result": f"Processed: {input_text}"}
    model.my_feature = my_feature
    return {"name": "my_plugin", "version": "1.0.0"}
```

Plugins are auto-discovered by `client.plugins.load_all_plugins()`.
