@echo off
setlocal
cd /d "%~dp0"

echo Starting RealAI-clean local inference (Vulkan llama-server)...
echo.
echo Preferred stack (orchestrator + UI):
echo   start_gpu_chat.bat
echo   OR  powershell -File scripts\run_local_chat.ps1
echo.
echo This script starts ONLY the Vulkan backend on :8080.
echo For chat/API use orchestrator on :8001 after this is healthy.
echo.
echo Press Ctrl+C to stop the server
echo.

set "LLAMA=C:\llama-vulkan\llama-server.exe"
set "REALAI_MODELS_DIR=C:\models\checkpoints_lora"
if not defined REALAI_CTX set REALAI_CTX=65536
if not defined REALAI_NGL set REALAI_NGL=99
REM Live weights: checkpoints_lora first, then llama-vulkan models, then package models
if defined REALAI_GGUF if exist "%REALAI_GGUF%" (
  set "MODEL=%REALAI_GGUF%"
) else (
  set "MODEL=C:\models\checkpoints_lora\qwen2.5-coder-7b-instruct-q5_k_m.gguf"
)
if not exist "%MODEL%" set "MODEL=C:\llama-vulkan\models\qwen2.5-coder-7b-instruct-q5_k_m.gguf"
if not exist "%MODEL%" set "MODEL=%~dp0models\qwen2.5-coder-7b-instruct-q5_k_m.gguf"

if not exist "%LLAMA%" (
  echo ERROR: Missing %LLAMA%
  echo Install/build llama-server with Vulkan, or set LLAMA path.
  pause
  exit /b 1
)
if not exist "%MODEL%" (
  echo ERROR: Missing model %MODEL%
  pause
  exit /b 1
)
echo Using model: %MODEL%
echo CTX=%REALAI_CTX%  NGL=%REALAI_NGL%

"%LLAMA%" ^
  -m "%MODEL%" ^
  --host 127.0.0.1 ^
  --port 8080 ^
  -c %REALAI_CTX% ^
  -ngl %REALAI_NGL% ^
  --jinja

pause
endlocal