@echo off
setlocal enabledelayedexpansion
REM Phase 4: body lives in scripts\windows\. Product home is two levels up.
cd /d "%~dp0..\.."
set "ROOT=%CD%"

REM ============================================================
REM RealAI-clean Vulkan GPU Launcher (FIXED for AMD Vulkan)
REM ============================================================

set PYTHONPATH=%ROOT%\;%PYTHONPATH%
if not defined REALAI_API_KEY set REALAI_API_KEY=local
if not defined REALAI_CTX set REALAI_CTX=65536
if not defined REALAI_NGL set REALAI_NGL=99
if not defined REALAI_GGUF set "REALAI_GGUF=C:\models\checkpoints_lora\qwen2.5-coder-7b-instruct-q5_k_m.gguf"

echo.
echo Checking for existing GPU server on port 8080...
echo.

REM ------------------------------------------------------------
REM CHECK IF GPU SERVER IS ALREADY RUNNING
REM ------------------------------------------------------------
curl -s -o nul -m 2 http://127.0.0.1:8080/health
if %ERRORLEVEL%==0 (
    echo GPU server already running.
    goto launch_stack
)

REM ------------------------------------------------------------
REM START GPU SERVER (llama-server.exe)
REM ------------------------------------------------------------
echo Starting GPU server: llama-server.exe

REM NOTE: llama-server has no "--vulkan" flag (Vulkan backend is compiled in
REM and auto-selected; ggml-vulkan.dll next to the exe is enough).
REM "--gpu-layers"/"-ngl" requires a NUMBER, not "all" -> use 999 to offload everything.
start "RealAI-Vulkan-GPU" cmd /c ^
    "C:\llama-vulkan\llama-server.exe ^
        -m %REALAI_GGUF% ^
        --host 0.0.0.0 ^
        --port 8080 ^
        -ngl %REALAI_NGL% ^
        -c %REALAI_CTX% ^
        --jinja"

REM ------------------------------------------------------------
REM WAIT FOR GPU SERVER TO COME ONLINE
REM ------------------------------------------------------------
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

REM ------------------------------------------------------------
REM LAUNCH ORCHESTRATOR + CHAT STACK
REM ------------------------------------------------------------
:launch_stack
echo Launching orchestrator + chat stack...

where pwsh >nul 2>&1
if %ERRORLEVEL%==0 (
    pwsh -ExecutionPolicy Bypass -File "%ROOT%\scripts\run_local_chat.ps1" %*
) else (
    powershell -ExecutionPolicy Bypass -File "%ROOT%\scripts\run_local_chat.ps1" %*
)

endlocal
