@echo off
setlocal
REM RealAI (:8081) vs Stockfish at its weakest level; live board at http://127.0.0.1:8765.
REM Starts the 3B on :8081 if needed (stops the 14B llama-server on :8080 first: both do not fit in 12 GB).
REM Usage: chess_match.bat [games=4] [--dry] [--help]   (extra args pass through)
set "PY=C:\venvs\realai-train\Scripts\python.exe"
cd /d C:\temp\chess-match
if /i "%~1"=="--help" (
  "%PY%" chess_vs_stockfish.py --help
  exit /b 0
)
set "DRY=0"
if /i "%~1"=="--dry" (set "DRY=1" & shift)
set "GAMES=4"
if not "%~1"=="" (set "GAMES=%~1" & shift)
set "WPORT=8081"
set "WAITS=120"
set "CMD="%PY%" chess_vs_stockfish.py --llm-url http://127.0.0.1:8081/v1/chat/completions --model realai-hive-3b --sf-skill 0 --games %GAMES% --remember --realai-home C:\RealAI-clean %1 %2 %3 %4 %5 %6"
powershell -NoProfile -Command "try { if ((Invoke-RestMethod http://127.0.0.1:%WPORT%/health -TimeoutSec 3).status -eq 'ok') { exit 0 } } catch {}; exit 1"
if errorlevel 1 (set "UP=0") else (set "UP=1")
if "%DRY%"=="1" (
  if "%UP%"=="1" (echo [dry] :8081 healthy - would use it) else (
    echo [dry] :8081 not healthy - would stop llama-server on 8080, run C:\RealAI-clean\scripts\windows\start_realai_hive_8081.bat, wait up to %WAITS%s
    call "C:\RealAI-clean\scripts\windows\stop_llama.bat" --dry 8080
  )
  echo [dry] %CMD%
  exit /b 0
)
if "%UP%"=="1" goto play
echo :8081 not healthy - freeing VRAM ^(stopping llama-server on 8080^) and starting the 3B...
call "C:\RealAI-clean\scripts\windows\stop_llama.bat" 8080
call "C:\RealAI-clean\scripts\windows\start_realai_hive_8081.bat"
if errorlevel 1 (
  echo Could not start :8081 ^(port held by something not answering /health, or model missing^).
  pause
  exit /b 1
)
echo Waiting for http://127.0.0.1:8081/health (up to %WAITS%s)...
powershell -NoProfile -Command "$d=(Get-Date).AddSeconds(%WAITS%); while((Get-Date) -lt $d){ try { if ((Invoke-RestMethod http://127.0.0.1:%WPORT%/health -TimeoutSec 3).status -eq 'ok') { exit 0 } } catch {}; Start-Sleep 3 }; exit 1"
if errorlevel 1 (
  echo TIMEOUT: :8081 did not become healthy in %WAITS%s. See the "RealAI hive :8081" window.
  pause
  exit /b 1
)
:play
%CMD%
pause
endlocal