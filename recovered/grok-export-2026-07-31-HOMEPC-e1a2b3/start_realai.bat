@echo off
setlocal enabledelayedexpansion

set ROOT=%~dp0
set VENV=%ROOT%.venv\Scripts\python.exe
set API_URL=http://127.0.0.1:8000

echo.
echo RealAI local startup
echo ====================
echo Root: %ROOT%
echo.

if not exist "%VENV%" (
  echo Python virtual environment not found at "%VENV%".
  echo Run: pip install -e .
  pause
  exit /b 1
)

echo Bootstrapping native weights if needed...
"%VENV%" -m realai.training.bootstrap_weights

if not defined REALAI_SELF_IMPROVE set REALAI_SELF_IMPROVE=1
if not defined REALAI_API_URL set REALAI_API_URL=%API_URL%

echo.
echo Starting RealAI server on %API_URL% ...
echo In another terminal: realai-build "your task"  OR  python -m realai.closed_loop
echo Press Ctrl+C to stop.
echo.
"%VENV%" -m realai.server.app

endlocal