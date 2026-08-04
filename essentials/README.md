# RealAi

**The Autonomous AI Core for Atomic Fizz & Beyond**

A powerful, modular, and extensible AI engine designed to power intelligent agents, game worlds, NPCs, and real-world applications.

---

## 🎯 Vision

RealAi is built to become a **true standalone AI system** — capable of reasoning, memory, tool use, self-improvement, and acting as the central intelligence layer for *Atomic Fizz: Wasteland GPS*.

---

## ✨ Key Features

- Multi-Provider Support (Grok, Hugging Face, OpenAI, Ollama)
- Advanced Agent System (Planner, Critic, Executor, etc.)
- Long-term Memory Engine
- Tool Integration (Web, Code, Web3, etc.)
- Voice Capabilities (ASR + TTS)
- Game Integration Ready (NPCs, Overseer, Quests, World Events)
- Self-Improvement Loop

---

## 🚀 Quick Start

```bash
git clone https://github.com/Unwrenchable/RealAi.git
cd RealAi

# Python setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Node.js frontend
pnpm install

# Configuration
cp realai.toml.example realai.toml
cp .env.example .env
```

### Local model & self-build (zero API spend)

```bash
python -m realai.training.bootstrap_weights
python -m realai.server.app   # terminal 1
```

```bash
export REALAI_API_URL=http://127.0.0.1:8000
realai-loop                   # health + agent + ingest + datasets
# python -m realai.closed_loop
# realai-build "implement feature X"
```

On Windows use `start_self_build.bat` or `set REALAI_API_URL=http://127.0.0.1:8000` then `realai-loop`.

Docs: [SELF_BUILD_LOCAL.md](docs/SELF_BUILD_LOCAL.md) · [REALAI_NATIVE_MODEL.md](docs/REALAI_NATIVE_MODEL.md)