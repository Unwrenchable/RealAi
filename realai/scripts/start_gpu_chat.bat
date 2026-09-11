@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM RealAI-clean Vulkan GPU Launcher (AMD Vulkan)
REM Binaries: C:\llama-vulkan\llama-server.exe (+ llama-cli.exe)
REM Weights : C:\models\checkpoints_lora
REM ============================================================

cd /d "%~dp0\.."
set PYTHONPATH=%CD%;%PYTHONPATH%
if not defined REALAI_API_KEY set REALAI_API_KEY=local
set REALAI_VULKAN_DIR=C:\llama-vulkan
set REALAI_MODELS_DIR=C:\models\checkpoints_lora
set REALAI_VRAM_SAFE=1
set REALAI_CRAFT_AUTOSTART=1
if not defined REALAI_GGUF set REALAI_GGUF=C:\models\checkpoints_lora\qwen2.5-coder-1.5b-instruct-q5_k_m.gguf
if not defined REALAI_NGL set REALAI_NGL=40
if not defined REALAI_CTX set REALAI_CTX=4096

echo.
echo Checking for existing GPU server on port 8080...
curl -s -o nul -m 2 http://127.0.0.1:8080/health
if %ERRORLEVEL%==0 (
    echo GPU server already running.
    goto launch_stack
)

echo Starting GPU server: C:\llama-vulkan\llama-server.exe
echo   Model: %REALAI_GGUF%
start "RealAI-Vulkan-GPU" cmd /c ^
    "C:\llama-vulkan\llama-server.exe ^
        -m \"%REALAI_GGUF%\" ^
        --host 127.0.0.1 ^
        --port 8080 ^
        -c %REALAI_CTX% ^
        -ngl %REALAI_NGL% ^
        --jinja"

echo Waiting for GPU server to initialize...
set /a tries=0
:wait_gpu
timeout /t 2 >nul
curl -s -o nul -m 2 http://127.0.0.1:8080/health
if %ERRORLEVEL%==0 goto gpu_ready
set /a tries+=1
if !tries! LSS 45 goto wait_gpu

echo WARNING: GPU server not responding yet.
goto launch_stack

:gpu_ready
echo GPU server is online.

:launch_stack
echo Launching orchestrator + Craft...
where pwsh >nul 2>&1
if %ERRORLEVEL%==0 (
    pwsh -ExecutionPolicy Bypass -File "%CD%\scripts\run_local_chat.ps1" -SkipUI -SkipPromote -SkipStart
) else (
    powershell -ExecutionPolicy Bypass -File "%CD%\scripts\run_local_chat.ps1" -SkipUI -SkipPromote -SkipStart
)
python -m realai.cli.craft
endlocal
