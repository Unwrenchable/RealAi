# Local image generation (SDXL-Turbo)
```text
==== Quick sequence (one-click bats) ====
  self_data.bat  ->  build_dataset.bat  ->  train_3b.bat (or train_1.5b.bat)
  ->  export_spotcheck_3b.bat (or export_spotcheck_1.5b.bat)  ->  chess_match.bat
  Interrupted training? Run resume_3b.bat / resume_1.5b.bat to continue from the last checkpoint.
  The train/resume bats stop the 8080/8081 llama-servers first; export_spotcheck starts :8081 and
  leaves it running (stop with stop_llama.bat 8081). MODELS.md / models_ledger.json update automatically.

==== Local image generation (SDXL-Turbo, no API keys) ====
  generate_image.bat "a guardian robot in a neon wasteland"
  (or double-click it and type a prompt). Output: C:\models\image\out\sdxl_<time>.png (folder opens).
  Weights: C:\models\image\sdxl-turbo (diffusers fp16). Runs on the RX 6700 XT via DirectML,
  512x512, 1 step (up to 4), guidance 0. Needs ~7 GB VRAM: stop the 14B first (stop_llama.bat 8080).
  In RealAI: ability image_generation uses SDXL-Turbo when the weights exist, otherwise the Pillow
  procedural fallback. The xAI path is removed. OpenAI-style handler:
  realai.local_sdxl.handle_images_generations({"prompt": "...", "size": "512x512"}).
  License: Stability AI Community License. Free for research, non-commercial use, and commercial use
  under US$1M annual revenue (commercial use requires registering at stability.ai/community-license).
  Show "Powered by Stability AI" and include the license text if you distribute it.

```
