# Travis speaker reference

Live XTTS clone: C:\models\checkpoints_lora\voices\unwrenchable_clip.wav (short)
Full YouTube-derived WAV (train source): C:\models\checkpoints_lora\voices\travis_speaker.wav
Also: myvoice (1).wav, unwrenchable.wav (same full take)

Env:
- REALAI_TTS_BACKEND=xtts
- REALAI_XTTS_SPEAKER=<clip for chat>
- REALAI_VOICE_TRAIN_WAV=<full wav for future fine-tune>

Do not run training from reconstruction agent.