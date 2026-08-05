@echo off
setlocal

REM Path to this folder
set ROOT=%~dp0

REM Correct API URL for RealAI server
set API_URL=http://127.0.0.1:8000

REM Only set REALAI_API_URL if not already set
if not defined REALAI_API_URL set REALAI_API_URL=%API_URL%

REM Enable self-improvement
if not defined REALAI_SELF_IMPROVE set REALAI_SELF_IMPROVE=1

REM Ensure Python exists
where python >nul 2>&1
if errorlevel 1 (
  echo Python not found on PATH.
  exit /b 1
)

REM Check server health
python -m realai.closed_loop --check-only
if errorlevel 1 (
  echo Server not ready. Start: python -m realai.server.app
  exit /b 1
)

REM Run builder loop
if "%~1"=="" (
  python -m realai.closed_loop
) else (
  python -m realai.closed_loop --task "%*"
)

endlocal
