@echo off
setlocal
REM RealAI (:8081) vs Stockfish at its weakest level; live board at http://127.0.0.1:8765.
REM Usage: chess_match.bat [games=4] [--help]   (extra args pass through)
set "PY=C:\venvs\realai-train\Scripts\python.exe"
cd /d C:\temp\chess-match
if /i "%~1"=="--help" (
  "%PY%" chess_vs_stockfish.py --help
  exit /b 0
)
set "GAMES=4"
if not "%~1"=="" (set "GAMES=%~1" & shift)
powershell -NoProfile -Command "try { if ((Invoke-RestMethod http://127.0.0.1:8081/health -TimeoutSec 3).status -eq 'ok') { exit 0 } } catch {}; exit 1"
if errorlevel 1 (
  echo :8081 is not healthy. Start it with C:\RealAI-clean\scripts\windows\start_realai_hive_8081.bat
  pause
  exit /b 1
)
"%PY%" chess_vs_stockfish.py --llm-url http://127.0.0.1:8081/v1/chat/completions --model realai-hive-3b --sf-skill 0 --games %GAMES% --remember --realai-home C:\RealAI-clean %1 %2 %3 %4 %5 %6
pause
endlocal