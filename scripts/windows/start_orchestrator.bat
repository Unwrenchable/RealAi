@echo off
REM RealAI-clean - orchestrator only (expects Vulkan already on :8080)
setlocal
REM Phase 4: body lives in scripts\windows\. Product home is two levels up.
cd /d "%~dp0..\.."
set "ROOT=%CD%"
REM Unquoted so the trailing backslash does not escape the closing quote.
set REALAI_HOME=%ROOT%\
set REALAI_ROOT=%ROOT%\
set REALAI_WORKSPACE=%ROOT%\
set "PYTHONPATH=%ROOT%\;%ROOT%\realai;%PYTHONPATH%"
set "REALAI_MODELS_DIR=C:\models\checkpoints_lora"
set "REALAI_LORA_ROOT=C:\models\checkpoints_lora"
set "REALAI_VULKAN_BASE=http://127.0.0.1:8080"
set "REALAI_API_BASE=http://127.0.0.1:8001"
set "REALAI_DEFAULT_MODEL=realai-default-coder"
set "REALAI_BACKEND_MODEL=qwen2.5-coder-7b-instruct-q5_k_m.gguf"
if not defined REALAI_GGUF set "REALAI_GGUF=C:\models\checkpoints_lora\qwen2.5-coder-7b-instruct-q5_k_m.gguf"
if not defined REALAI_CTX set "REALAI_CTX=65536"
if not defined REALAI_N_CTX set "REALAI_N_CTX=%REALAI_CTX%"
if not defined REALAI_NGL set "REALAI_NGL=99"
if not defined REALAI_API_KEY set "REALAI_API_KEY=local"
set "PYTHONUNBUFFERED=1"
if not exist "%ROOT%\logs" mkdir "%ROOT%\logs"

echo Starting RealAI v3 orchestrator on http://127.0.0.1:8001
echo Requires Vulkan llama-server on :8080 (start_realai_server.bat)
echo Logs: %ROOT%\logs\
echo.

python -m realai.v3_orchestrator --host 127.0.0.1 --port 8001
if errorlevel 1 pause
endlocal
