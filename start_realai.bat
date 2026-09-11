@echo off
REM ALIAS → start_all.bat (canonical). Prefer START_HERE.bat if unsure.
setlocal
cd /d "%~dp0"
echo [alias] start_realai.bat -^> start_all.bat
call "%~dp0start_all.bat" %*
endlocal

