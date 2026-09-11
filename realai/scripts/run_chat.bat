@echo off
REM RealAI-clean — full local chat stack (Vulkan + orchestrator)
cd /d "%~dp0\.."
set PYTHONPATH=%CD%;%PYTHONPATH%
set REALAI_VULKAN_DIR=C:\llama-vulkan
set REALAI_MODELS_DIR=C:\models\checkpoints_lora
set REALAI_VRAM_SAFE=1
if not defined REALAI_API_KEY set REALAI_API_KEY=local
if not defined REALAI_GGUF set REALAI_GGUF=C:\models\checkpoints_lora\qwen2.5-coder-1.5b-instruct-q5_k_m.gguf

where pwsh >nul 2>&1
if %ERRORLEVEL%==0 (
  pwsh -ExecutionPolicy Bypass -File "%CD%\scripts\run_local_chat.ps1" %*
) else (
  powershell -ExecutionPolicy Bypass -File "%CD%\scripts\run_local_chat.ps1" %*
)
