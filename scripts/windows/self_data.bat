@echo off
setlocal
REM Self-data loop vs the 14B teacher on :8080, then improve. Starts the 14B if :8080 is not healthy.
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
set "GEN="%PY%" -m realai.training.self_data generate --base-url http://127.0.0.1:8080 --minutes %MIN% --max-rows %ROWS% --plan auto"
set "IMP="%PY%" -m realai.training.self_data improve"
set "WPORT=8080"
set "WAITS=240"
powershell -NoProfile -Command "try { if ((Invoke-RestMethod http://127.0.0.1:%WPORT%/health -TimeoutSec 3).status -eq 'ok') { exit 0 } } catch {}; exit 1"
if errorlevel 1 (set "UP=0") else (set "UP=1")
if "%DRY%"=="1" (
  if "%UP%"=="1" (echo [dry] :8080 healthy - would use it) else (echo [dry] :8080 not healthy - would run C:\RealAI-clean\scripts\windows\start_qwen3_14b_live.bat and wait up to %WAITS%s)
  echo [dry] %GEN%
  echo [dry] %IMP%
  exit /b 0
)
if "%UP%"=="1" goto run
echo :8080 not healthy - starting Qwen3-14B (C:\RealAI-clean\scripts\windows\start_qwen3_14b_live.bat)...
call "C:\RealAI-clean\scripts\windows\start_qwen3_14b_live.bat"
if errorlevel 1 (
  echo Could not start the 14B: port 8080 is held by something that is not answering /health.
  echo Check it, or free it with C:\RealAI-clean\scripts\windows\stop_llama.bat 8080, then rerun.
  pause
  exit /b 1
)
echo Waiting for http://127.0.0.1:8080/health (up to %WAITS%s)...
powershell -NoProfile -Command "$d=(Get-Date).AddSeconds(%WAITS%); while((Get-Date) -lt $d){ try { if ((Invoke-RestMethod http://127.0.0.1:%WPORT%/health -TimeoutSec 3).status -eq 'ok') { exit 0 } } catch {}; Start-Sleep 3 }; exit 1"
if errorlevel 1 (
  echo TIMEOUT: :8080 did not become healthy in %WAITS%s. See the "RealAI Qwen3-14B :8080" window.
  pause
  exit /b 1
)
:run
echo :8080 healthy.
%GEN%
%IMP%
pause
endlocal