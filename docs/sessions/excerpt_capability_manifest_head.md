# **📄 1. REALAI CAPABILITY MANIFEST — SINGLE PAGE (v3 Unified Runtime)**

## **Identity**
RealAI is a **local‑first, provider‑grade intelligence engine** with its own runtime, model family, memory ecosystem, agent hierarchy, tool/plugin architecture, and OpenAI‑compatible API surface.  
It is not a wrapper.  
It is a full provider.

---

## **1. Core Runtime**
- Unified API server (`/v1/*`)  
- Structured router with validation, fallback, provider scoring  
- OpenAI‑compatible endpoints  
- Multi‑backend inference (llama.cpp, vLLM stubs, RealAI models)  
- Deterministic error envelopes  

---

## **2. Model & Provider System**
- RealAI model family (`realai-*`, `realai-embed`, overseer, vision)  
- Provider abstraction with routing, scoring, circuit breakers  
- Local‑first mode with external fallback  
- Canonical model registry with capability graph  

---

## **3. Memory & Knowledge**
- Multi‑store memory engine (SQLite, JSON episodic logs, vector stubs)  
- Summarization + long‑term memory  
- Knowledge graph + world‑state persistence  
- Memory endpoints: store, forget, query  

---

## **4. Agent System**
Hierarchical agent runtime with explicit cognitive roles:

- Planner  
- Critic  
- Executor  
- Worker  
- Synthesizer  
- Safety  
- Coding Agent  
- Identity / Self‑improvement loops  

---

## **5. Tools, Plugins & Skills**
- Declarative tool manifests  
- Permissioned execution model  
- Plugin loader lifecycle  
- Web, code, file, Web3, voice, automation tools  
- Skill registry + sandboxing  
- Future expansion: **44 Synthetic Organs**  

---

## **6. Universe Mode**
- Every repo = a universe  
- Multi‑workspace map  
- Knowledge graph across worlds  
- Universal agent dispatcher  
- Cross‑world learning  

---

## **7. Frontends & Developer Surfaces**
- Fusion UI  
- Next.js streaming chat UI  
- Desktop GUI  
- VS Code extension  
- Python SDK  
- TypeScript SDK  
- CLI  

---

## **8. Training & Evolution**
- Training scaffolding  
- Self‑improvement loops  
- Data flywheel  
- World‑state learning  
- NPC/quest generation lineage  

---

## **9. Deployment**
- Local GPU (llama.cpp, Vulkan, DirectML)  
- Docker  
- Windows, WSL, Linux  
- RealAI Craft portable CLI  

---

## **10. Philosophy**
RealAI is a **unified intelligence**, not a collection of modules.

---

# **📐 2. REALAI ARCHITECTURE DIAGRAM (TEXT‑BASED)**

```
                          ┌──────────────────────────┐
                          │      Universe Mode       │
                          │  (multi‑workspace map)   │
                          └────────────┬─────────────┘
                                       │
                          ┌────────────▼─────────────┐
                          │     Agent Orchestrator    │
                          │  Planner / Critic / Exec  │
                          └────────────┬─────────────┘
                                       │
        ┌──────────────────────────────┼──────────────────────────────┐
        │                              │                              │
┌───────▼────────┐           ┌─────────▼────────┐           ┌─────────▼────────┐
