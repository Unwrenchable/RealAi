@echo off
setlocal
REM Self-data loop vs the 14B teacher on :8080, then improve.
REM Usage: self_data.bat [minutes=30] [max_rows=800] [--dry]
set "PY=C:\venvs\realai-train\Scripts\python.exe"
for /f "delims==" %%V in ('set REALAI_ 2^>nul') do set "%%V="
set "REALAI_HOME=C:\temp\realai-dsb-sources"
cd /d "%REALAI_HOME%"
set "MIN="
set "ROWS="
set "DRY=0"
:args
if "%~1"=="" goto defaults
if /i "%~1"=="--help" goto usage
if /i "%~1"=="--dry" (set "DRY=1" & shift & goto args)
if not defined MIN (set "MIN=%~1") else (set "ROWS=%~1")
shift
goto args
:usage
echo self_data.bat [minutes=30] [max_rows=800] [--dry]
exit /b 0
:defaults
if not defined MIN set "MIN=30"
if not defined ROWS set "ROWS=800"
:run
set "GEN="%PY%" -m realai.training.self_data generate --base-url http://127.0.0.1:8080 --minutes %MIN% --max-rows %ROWS% --plan auto"
set "IMP="%PY%" -m realai.training.self_data improve"
if "%DRY%"=="1" (
  echo [dry] %GEN%
  echo [dry] %IMP%
  exit /b 0
)
powershell -NoProfile -Command "try { if ((Invoke-RestMethod http://127.0.0.1:8080/health -TimeoutSec 3).status -eq 'ok') { exit 0 } } catch {}; exit 1"
if errorlevel 1 (
  echo :8080 is not healthy. Start it with C:\RealAI-clean\scripts\windows\start_qwen3_14b_live.bat
  pause
  exit /b 1
)
%GEN%
%IMP%
pause
endlocal