@echo off
REM RealAI current best (realai-hive-3b, spot-check 11/16, non-default) on :8081, RX 6700 XT (Vulkan1).
REM Override the model: set REALAI_8081_GGUF=<path> before running.
if not defined REALAI_8081_GGUF set "REALAI_8081_GGUF=C:\models\checkpoints_lora\gguf\realai-hive-3b-20261011-Q5_K_M.gguf"
if not exist "%REALAI_8081_GGUF%" (
  echo Missing model %REALAI_8081_GGUF%
  exit /b 1
)
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 8081 -State Listen -EA SilentlyContinue) { exit 1 } else { exit 0 }"
if errorlevel 1 (
  echo Port 8081 is already in use. Not starting.
  exit /b 1
)
start "RealAI hive :8081" cmd /k ""C:\llama-vulkan\llama-server.exe" -m "%REALAI_8081_GGUF%" --alias realai-hive-3b --host 127.0.0.1 --port 8081 -c 4096 -ngl 99 --device Vulkan1 --jinja -fa off"
echo Started %REALAI_8081_GGUF% on http://127.0.0.1:8081 (check /health)