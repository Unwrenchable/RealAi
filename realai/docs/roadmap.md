# RealAI 3.0 – 12-Week Implementation Plan

## Week 1–2 – Core API + Config

- Implement `/v1/chat/completions`, `/v1/embeddings`, `/v1/models`.
- Add `realai.toml`, `models.yaml`, `providers.yaml`.
- Refactor: move server into `apps/api`, contracts into `core/api`.

## Week 3–4 – Local Models & Embeddings

- Integrate vLLM + llama.cpp adapters behind a unified interface.
- Add default open model auto-download.
- Implement embeddings backend and wire `/v1/embeddings` to it.

## Week 5–6 – Memory & Tools

- Implement `MemoryStore` (SQLite + FAISS/Chroma).
- Wire memory into chat pipeline (summaries + retrieval).
- Define tool schema and built-in tools (web, code, file).

## Week 7–8 – Agents & Tasks

- Implement `Agent` interfaces + planner/worker/critic agents.
- Build simple task graph executor.
- Expose `/v1/tasks` endpoint for multi-step jobs.

## Week 9–10 – Web3 & Voice (MVP)

- Add Solana adapter (read + simulate).
- Add basic ASR/TTS via external libraries (local where possible).
- Wire Web3 tool + voice mode into desktop app.

## Week 11–12 – Training Skeleton & Hardening

- Create `training/` pipelines (SFT skeleton, eval harness).
- Add logging, metrics, health checks, rate limiting.
- Document `REALAI_3.0.md`, architecture diagrams, extension guides.

