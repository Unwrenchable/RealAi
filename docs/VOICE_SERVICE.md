# Local voice as a shared service (decision 4, 2026-10-16)

## Merge result
- **Canonical engine: `realai/voice/tts_engine.py`, unchanged.** It already contains every def from all three versions:
  - Kokoro and XTTS local synthesis: `_synthesize_http`, `_ensure_local` and `_synthesize_local` on `KokoroTTS` and `XTTSBackend`;
  - `WindowsSAPI`, `_is_real_wav`, `MIN_REAL_WAV`, `_apply_provider_config`, `_maybe_clip_speaker_wav`, `_patch_torchaudio_load_soundfile`.
- **`.learn_cache/.../realai/voice/tts_engine.py`** is byte-identical apart from CRLF line endings. Nothing to recover.
- **`agent_tools/tts_engine.py`** (157 lines) was the oldest phase: HTTP-only, with a Kokoro timeout of 30s and default order kokoro→fish→xtts→piper. It could not be imported because `agent_tools` has no `tts_base`/`tts_piper`. Every def it had is a subset of the canonical engine, so it is now a shim that re-exports the canonical engine. The behaviour differences are intentional later fixes, not lost features: the 8s HTTP probe so local fallback kicks in fast, and xtts first.

## Recommendation (implemented): a separate client package, `realai/voice_service/`
The Voice Lab / voice trainer (`realai/voice/`: `lab_server.py` API on :8890, Vite UI on :8787, scripts, `start_voice_lab.*`) imports `tts_engine` through `provider.py`. So the shared service is built **next to** it, not inside it:
- No file under `realai/voice/` is edited.
- The service never starts, stops or restarts the lab or trainer.
- **Lab first.** `VoiceClient.speak()` calls the running lab API (`POST /v1/audio/speech`, `response_format: json`). The lab process already holds the Kokoro/XTTS weights, so nothing loads twice and the trainer is not disturbed.
- **Engine fallback.** If the lab is down and `REALAI_VOICE_MODE` is `auto` (the default) or `engine`, the client imports `realai.voice.provider` / `tts_engine` read-only, in-process. Set `REALAI_VOICE_MODE=lab` to forbid in-process model loads, which keeps the GPU free for the trainer or the 14B.
- **Silent stub check.** Stub WAVs are rejected with the canonical `_is_real_wav`.
- **Output.** WAV files go to `REALAI_VOICE_OUT`, defaulting to `<REALAI_HOME>/voice_out`.

## Who calls it
| Caller | How |
|---|---|
| Hive / orchestrator | `ability.voice_service` (`abilities/voice_service.py`), through the registry fall-through: `{"action":"speak","text":...}` or `{"action":"health"}` |
| Agents | `from realai.voice_service import speak, health, get_voice_client` |
| CLI | `python -m realai.voice_service health` / `speak "text" --voice laura --out x.wav` |
| UI | optional `python -m realai.voice_service serve` on **127.0.0.1:8891**: `GET /v1/voice-service/health`, `POST /v1/voice-service/speak`. It refuses 8890/8787/8000/8001/8080 and is never auto-started. |

**Routed (Travis, 2026-10-17).** The orchestrator `voice_health`, `voice_inventory`, `voice_speak` and `voice_listen` tools (`v3_orchestrator._run_tool`) now dispatch through `realai/voice_service/hive.py`, and `abilities/audio_speech.py` calls `get_voice_client().speak(save=False)`. Both are lab-first (Voice Lab API on :8890 when it is up) with an in-process engine fallback. Tool names, argument shapes and result keys are unchanged, plus a `route` field. `voice_listen` keeps the vosk `audio_transcription` ability as a last resort. The voice trainer and lab (`realai/voice/`) are untouched; `realai.voice.hive_tools` stays as the schema source and as the legacy direct path.

Note: `VoiceProvider.speak()` sets `REALAI_TTS_BACKEND`/`REALAI_KOKORO_VOICE` in `os.environ`, which is process-global. That is one more reason the service prefers the lab over in-process calls when several callers share a process.
