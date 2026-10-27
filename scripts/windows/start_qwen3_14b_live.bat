@echo off
REM Qwen3-14B on :8080, RX 6700 XT (Vulkan1). Canonical launcher (2026-10-12).
REM -fa off: -fa on garbles output on this Vulkan build (b9717).
REM -c 8192: with fa off, 16K context OOMs. No -ctk/-ctv q8_0: quantized V cache needs flash attention.
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8080 -State Listen -EA SilentlyContinue) { exit 1 } else { exit 0 }"
if errorlevel 1 (
  echo Port 8080 is already in use. Not starting Qwen3-14B.
  exit /b 1
)
start "RealAI Qwen3-14B :8080" cmd /k ""C:\llama-vulkan\llama-server.exe" -m "C:\models\checkpoints_lora\Qwen3-14B-Q4_K_M.gguf" --alias qwen3-14b --host 127.0.0.1 --port 8080 -c 8192 -ngl 99 --device Vulkan1 --jinja --reasoning off -fa off --temp 0.7 --top-p 0.8 --top-k 20 --min-p 0"
echo Started Qwen3-14B on http://127.0.0.1:8080 (check /health)