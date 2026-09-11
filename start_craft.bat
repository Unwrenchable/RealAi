@echo off
REM ============================================================
REM RealAI Craft - one-click startup
REM   Vulkan : C:\llama-vulkan\llama-server.exe
REM   Models : C:\models\checkpoints_lora
REM   Default GGUF: qwen2.5-coder-7b-instruct-q5_k_m.gguf
REM   Context: 65536  GPU layers: 99
REM ============================================================
setlocal
cd /d "%~dp0"

set "REALAI_HOME=%~dp0"
set "REALAI_ROOT=%~dp0"
set "REALAI_WORKSPACE=%~dp0"
set "PYTHONPATH=%~dp0;%~dp0realai;%PYTHONPATH%"
set "REALAI_VULKAN_DIR=C:\llama-vulkan"
set "REALAI_MODELS_DIR=C:\models\checkpoints_lora"
set "REALAI_LORA_ROOT=C:\models\checkpoints_lora"
set "REALAI_VULKAN_BASE=http://127.0.0.1:8080"
set "REALAI_API_BASE=http://127.0.0.1:8001"
set "REALAI_CRAFT_AUTOSTART=1"
set "REALAI_VRAM_SAFE=0"
set "REALAI_SELF_IMPROVE=1"
if not defined REALAI_GGUF set "REALAI_GGUF=C:\models\checkpoints_lora\qwen2.5-coder-7b-instruct-q5_k_m.gguf"
if not defined REALAI_NGL set "REALAI_NGL=99"
if not defined REALAI_CTX set "REALAI_CTX=65536"
if not defined REALAI_DEFAULT_MODEL set "REALAI_DEFAULT_MODEL=realai-hive"
if not defined REALAI_API_KEY set "REALAI_API_KEY=local"

where python >nul 2>&1
if errorlevel 1 (
  echo Python not found on PATH.
  pause
  exit /b 1
)

echo.
echo RealAI Craft one-click
echo   Vulkan exe : %REALAI_VULKAN_DIR%\llama-server.exe
echo   GGUF       : %REALAI_GGUF%
echo   CTX / NGL  : %REALAI_CTX% / %REALAI_NGL%
echo   Autostart  : ON
echo.

python -m realai.cli.craft %*
set "EC=%ERRORLEVEL%"
echo.
pause
exit /b %EC%