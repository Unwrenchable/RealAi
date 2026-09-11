# RealAI Voice Lab

Provider-level local voice stack for the RealAI hive bot.

**No Grok / xAI cloud TTS.** All speech is local.

## Paths

| Role | Path |
|------|------|
| TTS weights | `C:\models\checkpoints_lora` (Kokoro, fish_speech_s1, xtts_v2) |
| AMD Vulkan llama-server | `C:\llama-vulkan` → `:8080` |
| Fallback llama | `C:\llama` |
| DirectML runtime | `C:\DirectML` |
| Hive orchestrator | `:8001` |
| Voice Lab API | `:8890` |
| Voice Lab UI | `:8787` |

## Python provider

```text
realai.voice.provider      # VoiceProvider — speak / listen / health / inventory
realai.voice.tts_engine    # Kokoro → Fish → XTTS → Windows SAPI → Piper
realai.voice.hive_tools    # voice_speak, voice_inventory, voice_health, voice_listen
realai.voice.lab_server    # HTTP API on :8890
realai.providers.voice     # provider registration
```

Start the lab API:

```bat
python -m realai.voice.lab_server
```

Speak from hive / Python:

```python
from realai.voice import get_voice_provider
get_voice_provider().speak("RealAI is online.", as_base64=True)
```

Bot voice is enabled via `personas/bot.config.json` → `voice.enabled` or `REALAI_BOT_VOICE=1`.

## UI

```bat
cd C:\RealAI-clean\realai\voice
npm run dev
```

Opens on `http://127.0.0.1:8787` (does not steal Vulkan `:8080`).
