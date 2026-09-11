@echo off
setlocal

REM --- Ensure working directory is RealAI root ---
cd /d "%~dp0"
set "REALAI_HOME=%~dp0"
set "REALAI_ROOT=%~dp0"
set "PYTHONPATH=%~dp0;%PYTHONPATH%"

REM --- API base for local chat stack ---
set "API_URL=http://127.0.0.1:8001"

if not defined REALAI_API_URL  set "REALAI_API_URL=%API_URL%"
if not defined REALAI_API_BASE set "REALAI_API_BASE=%API_URL%"
if not defined REALAI_SELF_IMPROVE set "REALAI_SELF_IMPROVE=1"
if not defined REALAI_DEFAULT_MODEL set "REALAI_DEFAULT_MODEL=realai-default-coder"

REM --- Ensure Python is available ---
where python >nul 2>&1
if errorlevel 1 (
  echo Python not found on PATH.
  exit /b 1
)

REM --- Check if RealAI server is running ---
python -m realai.closed_loop --check-only
if errorlevel 1 (
  echo Server not ready. Start chat stack first:
  echo   realai-stack
  echo   OR  powershell -File scripts\run_local_chat.ps1 -SkipUI
  exit /b 1
)

REM --- Run closed loop with or without task argument ---
if "%~1"=="" (
  python -m realai.closed_loop
) else (
  python -m realai.closed_loop --task "%~*"
)

endlocal
