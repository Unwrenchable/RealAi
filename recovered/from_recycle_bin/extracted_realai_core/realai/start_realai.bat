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

echo Running health checks...
"%VENV%" -m realai.cli.realai_cli doctor
if errorlevel 1 (
  echo.
  echo Health checks reported a problem. Continuing to start the server anyway.
  echo.
)

if not defined REALAI_SELF_IMPROVE set REALAI_SELF_IMPROVE=0

echo.
echo Starting RealAI server on %API_URL% ...
echo Press Ctrl+C to stop.
echo.
"%VENV%" -m realai.cli.realai_cli serve --host 127.0.0.1 --port 8000

endlocal