@echo off
setlocal
set ROOT=%~dp0
set API_URL=http://127.0.0.1:8000
if not defined REALAI_API_URL set REALAI_API_URL=%API_URL%
if not defined REALAI_SELF_IMPROVE set REALAI_SELF_IMPROVE=1

where python >nul 2>&1
if errorlevel 1 (
  echo Python not found on PATH.
  exit /b 1
)

python -m realai.closed_loop --check-only
if errorlevel 1 (
  echo Server not ready. Start: python -m realai.server.app
  exit /b 1
)

if "%~1"=="" (
  python -m realai.closed_loop
) else (
  python -m realai.closed_loop --task "%~*"
)
endlocal