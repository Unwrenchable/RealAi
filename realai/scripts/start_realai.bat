@echo off
setlocal enabledelayedexpansion
REM Package-local launcher → workspace root (C:\RealAI-clean)
cd /d "%~dp0\.."

set "ROOT=%CD%"
set "REALAI_HOME=%ROOT%"
set "REALAI_ROOT=%ROOT%"
set "PYTHONPATH=%ROOT%;%PYTHONPATH%"
set "REALAI_VULKAN_DIR=C:\llama-vulkan"
set "REALAI_MODELS_DIR=C:\models\checkpoints_lora"
set "REALAI_CRAFT_AUTOSTART=1"
set "REALAI_VRAM_SAFE=1"
set "REALAI_SELF_IMPROVE=1"
set "API_URL=http://127.0.0.1:8001"
if not defined REALAI_API_URL set "REALAI_API_URL=%API_URL%"
if not defined REALAI_API_BASE set "REALAI_API_BASE=%API_URL%"
if not defined REALAI_DEFAULT_MODEL set "REALAI_DEFAULT_MODEL=realai-default-coder"
if not defined REALAI_GGUF set "REALAI_GGUF=C:\models\checkpoints_lora\qwen2.5-coder-1.5b-instruct-q5_k_m.gguf"

echo.
echo RealAI-clean local startup
echo ==========================
echo Root: %ROOT%
echo GGUF: %REALAI_GGUF%
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo Python not found on PATH.
  pause
  exit /b 1
)

echo Starting chat stack (Vulkan + orchestrator)...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\scripts\run_local_chat.ps1" -SkipUI -SkipPromote
echo.
echo Launching Craft (autostart)...
python -m realai.cli.craft
endlocal
