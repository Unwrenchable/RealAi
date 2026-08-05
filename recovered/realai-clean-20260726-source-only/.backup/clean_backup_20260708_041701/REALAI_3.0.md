# RealAI 3.0 – Vision

## What RealAI Is

RealAI is a **local-first, OpenAI-compatible AI provider** designed to be the best **operator** for:

- Infrastructure and deployment
- Web3 (Solana/EVM)
- Multi-agent orchestration
- Automation and tooling

RealAI is not just a router to other models. It is a **full provider** with:

- Its own model family (`realai-*`)
- Its own embeddings
- Its own memory and tools
- Its own agent framework

---

## Core Principles

- **Local-first:** Everything should be able to run on a single machine.
- **OpenAI-compatible:** Drop-in replacement for OpenAI APIs where possible.
- **Operator-grade:** Biased toward reliability, tooling, and execution over “chatty” personality.
- **Composable:** Models, tools, agents, and plugins are all swappable modules.
- **Transparent:** Clear configs, explicit permissions, observable behavior.

---

## Pillars of RealAI 3.0

### 1. Provider-grade API

- `/v1/chat/completions` (tools + streaming)
- `/v1/embeddings`
- `/v1/audio/transcriptions` and `/v1/audio/speech`
- `/v1/images/generations`
- `/v1/models`

### 2. Local Intelligence

- Default local model (`realai-default-8b`)
- vLLM + llama.cpp backends
- RealAI embeddings model
- Unified sampling and routing layer

### 3. Memory & Tools

- Vector memory with per-user collections
- Conversation summaries and long-term profiles
- Declarative tools with permissions and sandboxing
- Built-in tools: web, code, web3, file, calendar

### 4. Agents & Orchestration

- Planner, worker, critic, synthesizer agents
- Task graph executor
- `/v1/tasks` endpoint for multi-step jobs

### 5. Voice & Web3

- Local ASR + TTS
- Streaming voice conversations
- Solana/EVM adapters with policy-guarded execution

### 6. RealAI Model Family

- `realai-1.0-base`
- `realai-1.0-instruct`
- `realai-1.0-web3`
- Training + evaluation pipelines in-repo

---

## North Star

RealAI 3.0 should feel like:

> “If I give it my infra, my chain, and my tools, it can **run my stack**.”

Not just answer questions about it.

