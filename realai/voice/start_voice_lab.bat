@echo off
REM RealAI Voice Lab — API :8890 + full Studio UI :8787 (model pick + clone/train).
REM PowerShell:  cd C:\RealAI-clean ; .\realai\voice\start_voice_lab.ps1
setlocal EnableExtensions
cd /d "%~dp0..\.."
set "REALAI_HOME=%CD%"
set "REALAI_ROOT=%CD%"
set "REALAI_PRODUCT_ROOT=%CD%"
set "PYTHONPATH=%CD%;%CD%\realai;%PYTHONPATH%"
set "REALAI_MODELS_DIR=C:\models\checkpoints_lora"
set "REALAI_BOT_VOICE=1"
if not defined REALAI_TTS_BACKEND set "REALAI_TTS_BACKEND=xtts"
if not defined REALAI_KOKORO_MODEL_DIR set "REALAI_KOKORO_MODEL_DIR=C:\models\checkpoints_lora\Kokoro"
if not defined REALAI_KOKORO_VOICE set "REALAI_KOKORO_VOICE=af_heart"
if not defined REALAI_XTTS_MODEL_DIR set "REALAI_XTTS_MODEL_DIR=C:\models\checkpoints_lora\xtts_v2"
if not defined REALAI_XTTS_SPEAKER set "REALAI_XTTS_SPEAKER=C:\models\checkpoints_lora\voices\unwrenchable.wav"
if not defined REALAI_VOICE_LAB_PORT set "REALAI_VOICE_LAB_PORT=8890"
if not defined REALAI_VOICE_UI_PORT set "REALAI_VOICE_UI_PORT=8787"
set "REALAI_VOICE_LAB_URL=http://127.0.0.1:%REALAI_VOICE_LAB_PORT%"
set "PYTHONUNBUFFERED=1"
if not exist "%CD%\logs" mkdir "%CD%\logs"

set "NPM=C:\Program Files\nodejs\npm.cmd"
if not exist "%NPM%" set "NPM=npm.cmd"

set "NO_UI="
echo.%*| findstr /I /C:"--no-ui" >nul && set "NO_UI=1"
set "SIMPLE="
echo.%*| findstr /I /C:"--simple" >nul && set "SIMPLE=1"

echo.
echo === RealAI Voice Lab ^(full Studio^) ===
echo   API     http://127.0.0.1:%REALAI_VOICE_LAB_PORT%
echo   Studio  http://127.0.0.1:%REALAI_VOICE_UI_PORT%   ^<- model pick / record / train
echo   Simple  http://127.0.0.1:8001/voice-lab/          ^(fallback^)
echo.

REM ---- API :8890 ----
python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:%REALAI_VOICE_LAB_PORT%/health', timeout=3); raise SystemExit(0 if r.status==200 else 1)" 1>nul 2>nul
if errorlevel 1 (
  python -c "import socket; s=socket.socket(); s.settimeout(0.4); r=s.connect_ex(('127.0.0.1', int(%REALAI_VOICE_LAB_PORT%))); s.close(); raise SystemExit(0 if r==0 else 1)" 1>nul 2>nul
  if not errorlevel 1 (
    echo Port %REALAI_VOICE_LAB_PORT% busy but unhealthy — recycling...
    call "%~dp0stop_voice_lab.bat"
    python -c "import time; time.sleep(1)" 1>nul 2>nul
  )
  echo Launching Voice Lab API...
  python -c "from scripts.unified_stack import _base_env, start_voice_lab; import os; e=_base_env(); os.environ.update(e); r=start_voice_lab(e, force=False); print(r.get('status'), r.get('url')); raise SystemExit(0 if r.get('ok') else 1)"
  if errorlevel 1 (
    set "XTTS_PY=%CD%\.venv-xtts\Scripts\python.exe"
    if not exist "%XTTS_PY%" set "XTTS_PY=python"
    start "RealAI-VoiceLab" /MIN cmd /c "cd /d \"%CD%\" && set PYTHONPATH=%CD%;%CD%\realai&& set REALAI_HOME=%CD%&& set REALAI_TTS_BACKEND=xtts&& set REALAI_MODELS_DIR=C:\models\checkpoints_lora&& set REALAI_XTTS_MODEL_DIR=C:\models\checkpoints_lora\xtts_v2&& set REALAI_XTTS_SPEAKER=C:\models\checkpoints_lora\voices\unwrenchable.wav&& set REALAI_KOKORO_MODEL_DIR=C:\models\checkpoints_lora\Kokoro&& set REALAI_KOKORO_VOICE=af_heart&& set PYTHONUNBUFFERED=1&& \"%XTTS_PY%\" -m realai.voice.lab_server --host 127.0.0.1 --port %REALAI_VOICE_LAB_PORT% >>logs\voice-lab.out.log 2>>logs\voice-lab.err.log"
    call :wait_url http://127.0.0.1:%REALAI_VOICE_LAB_PORT%/health 50
    if errorlevel 1 (
      echo FAILED API — see logs\voice-lab.err.log
      exit /b 1
    )
  )
) else (
  echo API already up on :%REALAI_VOICE_LAB_PORT%.
)

if defined NO_UI (
  echo Skipping UI ^(--no-ui^).
  exit /b 0
)

if defined SIMPLE (
  echo Opening simple Hive speak UI...
  python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health', timeout=3)" 1>nul 2>nul || echo WARN: Hive :8001 down — start_all.bat for /voice-lab/
  start "" "http://127.0.0.1:8001/voice-lab/"
  exit /b 0
)

REM ---- Full Studio UI :8787 (Speak / Clone / Pipeline) ----
python -c "import urllib.request; r=urllib.request.urlopen('http://127.0.0.1:%REALAI_VOICE_UI_PORT%/', timeout=3); raise SystemExit(0 if r.status==200 else 1)" 1>nul 2>nul
if errorlevel 1 (
  if not exist "%CD%\realai\voice\package.json" (
    echo WARN: Studio package missing — opening simple UI on :8001
    start "" "http://127.0.0.1:8001/voice-lab/"
    exit /b 0
  )
  if not exist "%NPM%" (
    where npm.cmd >nul 2>&1 || (
      echo WARN: npm.cmd not found — opening simple UI on :8001
      start "" "http://127.0.0.1:8001/voice-lab/"
      exit /b 0
    )
    for /f "delims=" %%i in ('where npm.cmd') do set "NPM=%%i" & goto :have_npm
  )
  :have_npm
  if not exist "%CD%\realai\voice\node_modules\" (
    echo Installing Studio deps ^(first run^)...
    pushd "%CD%\realai\voice"
    call "%NPM%" install --no-fund --no-audit
    popd
  )
  echo Launching full Studio on :%REALAI_VOICE_UI_PORT% ^(detached vite^)...
  python -c "from scripts.unified_stack import _base_env, start_voice_studio; import os; e=_base_env(); os.environ.update(e); r=start_voice_studio(e, force=False); print(r.get('status'), r.get('url')); raise SystemExit(0 if r.get('ok') else 1)"
  if errorlevel 1 (
    echo Studio failed/slow — see logs\voice-lab-ui.err.log
    echo Opening simple speak UI on Hive :8001 instead...
    start "" "http://127.0.0.1:8001/voice-lab/"
    exit /b 0
  )
) else (
  echo Studio already up on :%REALAI_VOICE_UI_PORT%.
)

echo Opening full Studio ^(Speak / Clone / Pipeline^)...
start "" "http://127.0.0.1:%REALAI_VOICE_UI_PORT%/"
echo.
echo Done.
echo   Studio: http://127.0.0.1:%REALAI_VOICE_UI_PORT%/
echo   API:    http://127.0.0.1:%REALAI_VOICE_LAB_PORT%/health
exit /b 0

:wait_url
set "URL=%~1"
set /a MAX=%~2
set /a N=0
:wait_loop
set /a N+=1
python -c "import urllib.request; r=urllib.request.urlopen('%URL%', timeout=2); raise SystemExit(0 if r.status==200 else 1)" 1>nul 2>nul
if not errorlevel 1 exit /b 0
if %N% GEQ %MAX% exit /b 1
REM Avoid `timeout` — breaks under redirected/non-interactive shells.
python -c "import time; time.sleep(1)" 1>nul 2>nul
goto wait_loop
