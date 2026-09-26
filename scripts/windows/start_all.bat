@echo off
REM ============================================================
REM RealAI unified one-click stack
REM   Vulkan :8080  +  Orch :8001  +  console speak-aloud
REM ============================================================
setlocal
REM Phase 4: body lives in scripts\windows\. Product home is two levels up.
cd /d "%~dp0..\.."
set "ROOT=%CD%"

REM Unquoted so the trailing backslash does not escape the closing quote.
set REALAI_HOME=%ROOT%\
set REALAI_ROOT=%ROOT%\
set REALAI_WORKSPACE=%ROOT%\
set "PYTHONPATH=%ROOT%\;%ROOT%\realai;%PYTHONPATH%"
set "REALAI_VULKAN_DIR=C:\llama-vulkan"
set "REALAI_MODELS_DIR=C:\models\checkpoints_lora"
set "REALAI_LORA_ROOT=C:\models\checkpoints_lora"
set "REALAI_API_BASE=http://127.0.0.1:8001"
set "REALAI_VULKAN_BASE=http://127.0.0.1:8080"
set "REALAI_BOT_LOCAL_ONLY=1"
set "REALAI_BOT_VOICE=1"
set "REALAI_BOT_TOOLS=1"
set "REALAI_SELF_IMPROVE=1"
set "REALAI_TTS_BACKEND=xtts"
if not defined REALAI_GGUF set "REALAI_GGUF=C:\models\checkpoints_lora\qwen2.5-coder-7b-instruct-q5_k_m.gguf"
if not defined REALAI_CTX set "REALAI_CTX=65536"
if not defined REALAI_N_CTX set "REALAI_N_CTX=%REALAI_CTX%"
if not defined REALAI_NGL set "REALAI_NGL=99"
set "REALAI_VRAM_SAFE=0"
if not defined REALAI_KOKORO_MODEL_DIR set "REALAI_KOKORO_MODEL_DIR=C:\models\checkpoints_lora\Kokoro"
if not defined REALAI_FISH_MODEL_DIR set "REALAI_FISH_MODEL_DIR=C:\models\checkpoints_lora\fish_speech_s1"
if not defined REALAI_XTTS_MODEL_DIR set "REALAI_XTTS_MODEL_DIR=C:\models\checkpoints_lora\xtts_v2"
if not defined REALAI_XTTS_SPEAKER set "REALAI_XTTS_SPEAKER=C:\models\checkpoints_lora\voices\unwrenchable_clip.wav"
if not defined REALAI_KOKORO_VOICE set "REALAI_KOKORO_VOICE=af_heart"

where python >nul 2>&1
if errorlevel 1 (
  echo Python not found on PATH.
  pause
  exit /b 1
)

echo.
echo RealAI unified stack  ^(canonical - see docs\RUN_SERVERS.md^)
echo   Product home: %CD%
echo   Package:      %CD%\realai
echo   Vulkan :8080
echo   Hive   :8001  console / fusion-ui / agents-ui
echo   Console http://127.0.0.1:8001/console
echo   Fusion  http://127.0.0.1:8001/fusion-ui/
echo   Agents  http://127.0.0.1:8001/agents-ui/
echo   Hive UI http://127.0.0.1:3000  ^(optional: start_ui.bat^)
echo   Voice Lab :8890  ^(launched with stack^)
echo   Provider: RealAI local - no xAI
echo.

python "%ROOT%\scripts\unified_stack.py" %*
set "EC=%ERRORLEVEL%"
echo.
if %EC%==0 (
  echo OK. Open http://127.0.0.1:8001/console ^(hard-refresh if already open^).
  echo Voice Lab http://127.0.0.1:8890/health
) else (
  echo FAILED. See logs\vulkan.err.log logs\v3-orchestrator.err.log logs\voice-lab.err.log
)
pause
exit /b %EC%
