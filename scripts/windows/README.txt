RealAI training helpers  (copies of C:\temp\realai-dsb-sources\scripts\windows\*.bat)
All use C:\venvs\realai-train\Scripts\python.exe and REALAI_HOME=C:\temp\realai-dsb-sources.
Servers: C:\RealAI-clean\scripts\windows\start_qwen3_14b_live.bat (:8080 14B teacher),
         start_realai_hive_8081.bat (:8081 RealAI 3B), stop_llama.bat [--dry] [ports].

One cycle:
  1. self_data.bat [minutes=30] [max_rows=800]   starts the 14B on :8080 if needed, generates verified rows, then improve
  2. build_dataset.bat                           rebuilds datasets\realai-hive-sft-<date> (no servers needed)
  3. train.bat 3b <run_name> [--resume]          stops 8080/8081 llama-servers after a 5s Ctrl+C window, trains on GPU
     train.bat 1.5b <run_name>                   (1.5B recipe defaults)
  4. export + spotcheck: export_spotcheck_3b.bat / export_spotcheck_1.5b.bat (manual equivalent):
       python -m realai.training.train_sft export --dataset <ds> --out runs\sft-<run> --base-model C:\models\hf\Qwen2.5-3B-Instruct --model-id <run>
       copy the GGUF to C:\models\checkpoints_lora\gguf\, set REALAI_8081_GGUF, run start_realai_hive_8081.bat
       python -m realai.training.spotcheck --model-id <run>   (and --no-tools)
  5. chess_match.bat [games]                     starts the 3B on :8081 (stops 8080 first), plays Stockfish skill 0, --remember

Every bat accepts --dry (self_data, chess_match) or --dry-run (train, build_dataset) to show what it would do.
Only 14B OR the 3B fits on the 12 GB RX 6700 XT at once.
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
