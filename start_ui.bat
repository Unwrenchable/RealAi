@echo off
REM RealAI Next.js App Router UI (canonical: product-root frontend\)
REM Console / fusion-ui shell assets remain served by hive orchestrator on :8001.
setlocal
cd /d "%~dp0"

set "REALAI_HOME=%~dp0"
set "REALAI_ROOT=%~dp0"
set "REALAI_API_BASE=http://127.0.0.1:8001"
set "REALAI_ORCH_URL=http://127.0.0.1:8001"
set "REALAI_DEFAULT_MODEL=realai-default-coder"
set "REALAI_BOT_LOCAL_ONLY=1"
set "REALAI_BOT_VOICE=1"
set "NEXT_PUBLIC_API_URL=http://127.0.0.1:8001"
REM Never point the hive brain at cloud providers
set "XAI_API_KEY="
set "OPENAI_API_KEY="
set "GROK_API_KEY="

where node >nul 2>&1
if errorlevel 1 (
  echo Node.js not found on PATH.
  pause
  exit /b 1
)

if not exist "frontend\package.json" (
  echo Canonical frontend missing: frontend\package.json
  pause
  exit /b 1
)

cd /d "%~dp0frontend"

if not exist "node_modules\" (
  echo Installing npm deps...
  call npm install
  if errorlevel 1 (
    echo npm install failed.
    pause
    exit /b 1
  )
)

echo.
echo RealAI Next UI on http://127.0.0.1:3000
echo Brain: local orch %REALAI_API_BASE%  (provider=RealAI, no xAI)
echo Make sure start_all.bat stack is up first.
echo.

call npm run dev
endlocal
