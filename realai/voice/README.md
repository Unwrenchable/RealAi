# RealAI Voice Lab

Local provider-level voice for the **RealAI hive bot**.

- Weights: `C:\models\checkpoints_lora` (Kokoro · Fish Speech · XTTS)
- Chat GPU: `C:\llama-vulkan` (AMD Vulkan) or `C:\llama`
- DirectML: `C:\DirectML`
- **No Grok / xAI cloud TTS**

## Quick start

```bat
REM API (hive + UI call this)
C:\RealAI-clean\realai\voice\start_voice_lab.bat

REM Optional UI
cd C:\RealAI-clean\realai\voice
npm run dev
```

| Service | Port |
|---------|------|
| Vulkan llama-server | 8080 |
| Hive orchestrator | 8001 |
| Voice Lab API | 8890 |
| Voice Lab UI | 8787 |

## Hive bot

Voice is on in `personas\bot.config.json`. Slash aliases:

```text
/speak Hello from RealAI
/voice
/voices
/tool voice_speak text="Hive bot speaking locally"
```

## Python

```python
from realai.voice import get_voice_provider, voice_inventory, stack_health

print(voice_inventory()["kokoro"]["voices"][:5])
print(stack_health()["vulkan"])
wav = get_voice_provider().speak("RealAI online.", as_base64=True)
```
