# RealAI Bot personas

## Boot

On API / GUI / CLI startup, `realai.bot.boot.register_default_bot()` registers the
**RealAI Bot** persona (idempotent) and switches to it.

```bash
cd C:\RealAI-clean
python -c "from realai.bot.boot import register_default_bot; print(register_default_bot())"
```

## Local-only rule

- Chat for this product bot uses **local / realai** providers only.
- `REALAI_BOT_LOCAL_ONLY=1` is the default (on).
- Do **not** route bot chat through Grok / xAI / OpenAI / Anthropic / Gemini.
- If the local backend is down, fail closed: `local model offline`.

## Files

| File | Role |
|------|------|
| `realai_bot.json` | Default persona + system prompt |
| `realai_bot.md` | Human-readable copy of the prompt |
| `bot.config.json` | Product name, memory namespace, routing |

Memory namespace: `persona_realai_bot`.

## Models (`C:\models\checkpoints_lora`)

Chat GGUFs and voice packs resolve from:

| Path | Role |
|------|------|
| `C:\models\checkpoints_lora\*.gguf` | Vulkan chat weights |
| `...\Kokoro\` | Kokoro TTS (`realai-voice-kokoro`) |
| `...\fish_speech_s1\` | Fish Speech (`realai-voice-fish`) |
| `...\xtts_v2\` | XTTS v2 (`realai-voice-xtts`) |

Env: `REALAI_MODELS_DIR`, `REALAI_GGUF`, `REALAI_KOKORO_MODEL_DIR`, `REALAI_FISH_MODEL_DIR`, `REALAI_XTTS_MODEL_DIR`, `REALAI_XTTS_SPEAKER`.

## Voice (from `C:\Users\tsmit\agent-tools\tts-stack`)

Voice helpers are live under `realai/voice/` + `realai/orchestration/tts_routing.py`.
Set `REALAI_BOT_VOICE=1` for `realai_meta.voice.spoken_text` on chat replies.
