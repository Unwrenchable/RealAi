Qwen3-14B (Q4_K_M) launchers for RealAI-clean
=============================================
Files:
  start_qwen3_14b_server.bat        llama-server on :8082 (alias qwen3-14b, ctx 16384, KV q8_0, thinking off)
  start_orchestrator_qwen3_14b.bat  orchestrator on :8002 pointed at :8082 (default model local-qwen3-14b-q4-k-m)

To switch to the 14B:
  1. STOP the 7B first (llama-server :8080, and the :8001 orchestrator if you want the VRAM/RAM back).
     The GPU has 12 GB VRAM; 7B@65536 ctx + 14B will not fit together.
  2. Run start_qwen3_14b_server.bat (override with QWEN3_PORT / QWEN3_CTX env vars if needed).
  3. Optionally run start_orchestrator_qwen3_14b.bat (port 8002).

To go back to the 7B:
  Stop both 14B windows (Ctrl+C), then start the normal start_realai_server.bat and start_orchestrator.bat.

These scripts do not modify config.json or any machine-level environment variable.
