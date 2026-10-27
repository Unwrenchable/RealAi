Qwen3-14B live server (port 8080)
=================================

Start:  double-click start_qwen3_14b_live.bat
  - Refuses to start (and pauses) if anything already listens on port 8080.
  - Otherwise opens a window titled "RealAI Qwen3-14B :8080" running
    C:\llama-vulkan\llama-server.exe with the Qwen3-14B-Q4_K_M model
    (alias qwen3-14b, 127.0.0.1:8080, 16k context).
  - Check: http://127.0.0.1:8080/health

Stop:   double-click stop_qwen3_14b_live.bat
  - Stops only the llama-server.exe whose command line contains
    "Qwen3-14B" and "--port 8080". Other processes are untouched.

Return to the 7B:
  1. Run stop_qwen3_14b_live.bat (frees port 8080).
  2. Run start_realai_server.bat.
