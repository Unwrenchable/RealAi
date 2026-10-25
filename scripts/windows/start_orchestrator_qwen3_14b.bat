@echo off
REM RealAI-clean - orchestrator for Qwen3-14B (expects start_qwen3_14b_server.bat on :8082). Listens on :8002.
setlocal
cd /d "%~dp0..\.."
set "ROOT=%CD%"
REM Unquoted so the trailing backslash does not escape the closing quote.
set REALAI_HOME=%ROOT%\
set REALAI_ROOT=%ROOT%\
set REALAI_WORKSPACE=%ROOT%\
set "PYTHONPATH=%ROOT%\;%ROOT%\realai;%PYTHONPATH%"
set "REALAI_MODELS_DIR=C:\models\checkpoints_lora"
set "REALAI_LORA_ROOT=C:\models\checkpoints_lora"
set "REALAI_VULKAN_BASE=http://127.0.0.1:8082"
set "REALAI_API_BASE=http://127.0.0.1:8002"
set "REALAI_DEFAULT_MODEL=local-qwen3-14b-q4-k-m"
set "REALAI_BACKEND_MODEL=Qwen3-14B-Q4_K_M.gguf"
set "REALAI_GGUF=C:\models\checkpoints_lora\Qwen3-14B-Q4_K_M.gguf"
set "REALAI_CTX=16384"
set "REALAI_N_CTX=16384"
if not defined REALAI_NGL set "REALAI_NGL=99"
if not defined REALAI_API_KEY set "REALAI_API_KEY=local"
set "PYTHONUNBUFFERED=1"
if not exist "%ROOT%\logs" mkdir "%ROOT%\logs"

echo Starting RealAI v3 orchestrator (Qwen3-14B) on http://127.0.0.1:8002
echo Requires llama-server on :8082 (start_qwen3_14b_server.bat)
echo Logs: %ROOT%\logs\
echo.

python -m realai.v3_orchestrator --host 127.0.0.1 --port 8002
if errorlevel 1 pause
endlocal
